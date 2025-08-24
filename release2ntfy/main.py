import asyncio
import logging
import re
from argparse import ArgumentParser

import yaml
from aiohttp import ClientSession
from benedict import benedict
from tabulate import tabulate
from termcolor import colored

from release2ntfy.constants import DATA_PATH
from release2ntfy.schemas import AppConfig, EventSourceConfig, ReleaseInfo
from release2ntfy.templates import KNOWN_TEMPLATES

parser = ArgumentParser(prog='release2ntfy')
parser.add_argument('-c', '--crontab', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-n', '--no-store', action='store_true')

args = parser.parse_args()

def apply_vars(source: str, variables: dict):
    result = source
    for var in variables:
        result = result.replace(f"${var}", str(variables[var]))
    return result


async def process_event(entry: EventSourceConfig, env: dict):
    variables = {**env, "ID": entry.id}

    log = logging.getLogger(f"main.{entry.id}")
    log.info(f"Fetching {entry.url}...")
    async with ClientSession() as session:
        headers = {x: apply_vars(y, variables) for x, y in entry.headers.items()}
        async with session.get(entry.url, headers=headers) as r:
            if r.status != entry.valid_status:
                raise ValueError(f"While fetching, status {r.status} != {entry.valid_status}, text {await r.text()}")
            payload = benedict(await r.json())

    with_index = "$INDEX" in entry.revision_path
    from_end = entry.index_mode == "last_match"
    index_all = entry.index_mode == "all"
    index = -1 if from_end else 0
    out = []

    while True:
        variables["INDEX"] = index

        # Find revision
        path = apply_vars(entry.revision_path, variables)
        log.debug(f"Trying to read {path} from payload")
        try:
            revision = payload[path]
        except KeyError:
            break

        # Check RegExp match
        suitable = True
        if entry.revision_regexp:
            suitable = re.compile(entry.revision_regexp).match(revision)

        # Process
        if suitable:
            log.info(f"Adding {revision} to release info")
            result_id = entry.id if not index_all else f"{entry.id}//{revision}"
            variables["REVISION"] = revision
            try:
                description = payload[apply_vars(entry.description_path, variables)]
                assert isinstance(description, str)
            except (KeyError, AssertionError):
                description = "(no description)"

            try:
                preview_url = payload[apply_vars(entry.preview_url_path, variables)]
                assert isinstance(preview_url, str)
            except (KeyError, AssertionError):
                preview_url = ""

            out.append(ReleaseInfo(
                id=str(result_id),
                revision=str(revision),
                description=str(description),
                preview_url=str(preview_url),
                title=str(apply_vars(entry.title, variables))
            ))

            if not index_all:
                break

        # Go to next one
        if not with_index:
            break
        elif from_end:
            index -= 1
        else:
            index += 1

    return out


async def process_all():
    # Load saved state and config
    with open(DATA_PATH / "state.yaml", "r") as f:
        state = yaml.load(f, yaml.Loader)
        if not state or args.no_store:
            state = {}
    with open(DATA_PATH / "config.yaml", "r") as f:
        config = AppConfig.model_validate(yaml.load(f, yaml.Loader))

    # Check all events
    out = []
    for e in config.events:
        if e.template != "":
            if e.template not in KNOWN_TEMPLATES:
                logging.error(f"Unknown template: {e.template}, event skipped")
                continue
            e = KNOWN_TEMPLATES[e.template](e)

        ret = await process_event(e, config.env)
        for row in ret:
            row.prev_revision = state.get(row.id, "")
            row.notify = row.prev_revision != row.revision
            out.append(row)

    # Print results
    print(tabulate(
        [(r.id, r.title, r.prev_revision,  colored(r.revision, "green" if r.notify else 'yellow')) for r in out],
        headers=['ID', 'Title', 'Prev revision', 'Revision'],
        tablefmt="simple_outline"
    ))

    # Send notifications and save state
    async with ClientSession(base_url=config.target.base_url) as session:
        log = logging.getLogger("send_ntfy")
        for row in out:
            if row.revision == row.prev_revision:
                continue

            payload = {
                "topic": config.target.topic,
                "title": row.title,
                "message": row.description,
                "tags": [config.target.icon_tag],
                "click": row.preview_url,
            }

            async with session.post("/", json=payload, ssl=not config.target.no_verify) as ret:
                if ret.status != 200:
                    log.error(f"While sending notification status {ret.status}, text {await ret.text()}")

            state[row.id] = row.revision

    # Create crontab, if required
    if args.crontab:
        with open("crontab", "w") as f:
            f.write(f"{config.cron_schedule} cd /app && /app/.venv/bin/python -m release2ntfy\n")

    # Save state
    if not args.no_store:
        with open(DATA_PATH / "state.yaml", "w") as f:
            yaml.dump(state, f, yaml.Dumper)


def main():
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.run(process_all())

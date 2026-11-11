# The Leaky Loop

This repo holds the analysis behind The Leaky Loop on milcahjoseph.com. `build_data.py` reads Eurostat's raw downloads from `data/raw` and writes the tables in `data/processed`.

## How to make changes

- Work directly on `main`: pull the latest version before starting, and push once the task is done.
- Commit as Milcah: before your first commit, run `git config user.name "Milcah M. Joseph"` and `git config user.email "98636311+M1ck3yJ0@users.noreply.github.com"`. End each commit message with a Co-Authored-By line naming the Claude model, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Add no session link.
- Work on one task at a time and change only what it asks for.
- Commit after every step, so each commit holds one small change: creating a folder, adding a file, making a separate edit. A new folder gets a `.gitkeep` file in its own commit.
- Give each commit a concise title, under 50 characters, and at most one line of description.
- Write rules in this file as plain instructions, without reasons.
- After pushing, give Milcah a clear list in the chat of what changed.
- Don't delete files unless she asks.

## Data

- Never commit Eurostat's raw downloads. `data/raw/README.md` lists each file and where to get it.
- Ask Milcah to upload the raw downloads before a rerun.
- After changing `build_data.py`, rerun it from the repo root, check the changed tables against the previous ones, and commit each changed table separately.
- Use American spelling and no em or en dashes in any text.

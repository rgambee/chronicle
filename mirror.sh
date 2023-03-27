#!/usr/bin/env bash

USAGE="Mirror the app to creata a static version suitable for serving from GitHub Pages

Credit goes to Michele Pasin for the approach this scipt uses.
https://www.michelepasin.org/blog/2021/10/29/django-wget-static-site/index.html

USAGE:
    bash ${0} [DIRECTORY]

ARGUMENTS:
    DIRECTORY: Path to folder where files will be saved. Does not need to already exist.
        Defaults to './mirrored/'.

OPTIONS:
    --help, -h: Show this help and exit

EXIT VALUES:
    - 0     Sucess
    - 1     Invalid option/argument
    - 2     App failed to launch
    - 3     App crashed while mirroring
    - 4     wget exited with error
"

REPO="$(dirname -- "${0}")"
PORT="8000"
MIRROR_DIRECTORY="${REPO}/mirrored/"
# Use the demo database (which is tracked in git) instead of the default (which isn't)
export CHRONICLE_DATABASE="${REPO}/demo.sqlite3"
# Run the app in read-only, demo mode
export CHRONICLE_DEMO_MODE=1

if [[ "${#}" = 1 ]]
then
    if [[ "${1}" = "-h" || "${1}" = "--help" ]]
    then
        echo "${USAGE}"
        exit 0
    fi
    MIRROR_DIRECTORY="${1}"
elif [[ "${#}" > 1 ]]
then
    echo "Invalid argument ${@}" >&2
    exit 1
fi

echo "Starting app in background"
python "${REPO}/manage.py" runserver "${PORT}" &
DJANGO_PID="${!}"

# Wait a bit for the app to launch
sleep 3

if ! ps -p "${DJANGO_PID}" > /dev/null
then
    echo "App failed to launch" >&2
    exit 2
fi
echo "App running successfully"

# Use wget to download all the served files and store them so they can later be
# used for a static version of the app.
# --directory-prefix
#   The directory prefix is the directory where all other files and
#   subdirectories will be saved to.
# --mirror
#   Turn on options suitable for mirroring, including recursion.
# --convert-links
#   After the download is complete, convert the links in the document to make
#   them suitable for local viewing.  This affects not only the visible
#   hyperlinks, but any part of the document that links to external content,
#   such as embedded images, links to style sheets, hyperlinks to non-HTML
#   content, etc.
# --adjust-extension
#   Append .html suffix to the local file name even if not in the URL.
# --page-requisites
#   This option causes Wget to download all the files that are necessary to
#   properly display a given HTML page.  This includes such things as inlined
#   images, sounds, and referenced stylesheets.
# --no-host-directories
#   Remove host prefix (http://127.0.0.1:8000/) from directory.
# --wait
#   Wait for content to fully load before saving.
# --no-verbose
#   Turn off verbose without being completely quiet, which means that error
#   messages and basic information still get printed.
echo "Mirroring site"
wget --directory-prefix="${MIRROR_DIRECTORY}" \
    --mirror \
    --convert-links \
    --adjust-extension \
    --page-requisites \
    --no-host-directories \
    --wait=1 \
    --no-verbose \
    http://127.0.0.1:"${PORT}"/
WGET_STATUS="${?}"

if ! ps -p "${DJANGO_PID}" > /dev/null
then
    echo "App crashed while mirroring" >&2
    exit 3
fi

echo "Interrupting app"
kill "${DJANGO_PID}"
wait

if [[ "${WGET_STATUS}" > 0 ]]
then
    echo "wget exited with status ${WGET_STATUS}" >&2
    exit 4
fi

echo "Site successfully mirrored to ${MIRROR_DIRECTORY}"

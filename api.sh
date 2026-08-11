#!/usr/bin/env sh

artist="$1"
title="$2"

curl "https://api.listenbrainz.org/1/metadata/lookup/?artist_name=$artist&recording_name=$title&metadata=false" \
  -H 'accept: application/json' \
  -H 'content-type: application/json' \
  -H "authorization: Token $LISTENBRAINZ_TOKEN"

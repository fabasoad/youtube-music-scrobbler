#!/usr/bin/env sh

main() {
  curl -H "Authorization: Token ${LISTENBRAINZ_TOKEN}" "https://api.listenbrainz.org/1/validate-token"
}

main "$@"

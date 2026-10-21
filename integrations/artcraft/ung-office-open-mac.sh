#!/usr/bin/env bash
# UNG Office desktop bridge: open existing documents with installed applications.
# No elevated privileges, arbitrary shell execution, or file conversion claims.
set -euo pipefail
usage(){ echo "Usage: bash $0 /absolute/path/to/document.{docx,xlsx,pptx,doc,xls,ppt,odt,ods,odp,pdf}" >&2; exit 2; }
[[ $# == 1 && -f "$1" ]] || usage
file="$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")"
ext="${file##*.}"
ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
case "$ext" in
 doc|docx|odt) candidates=(WordCraft "Microsoft Word") ;;
 xls|xlsx|ods) candidates=(GridCraft "Microsoft Excel") ;;
 ppt|pptx|odp) candidates=(DeckCraft "Microsoft PowerPoint") ;;
 pdf) candidates=(PdfCraft Preview) ;;
 *) echo "Unsupported document extension: .$ext" >&2; exit 2 ;;
esac
for app in "${candidates[@]}"; do
 for root in /Applications "$HOME/Applications"; do
   bundle="$root/$app.app"
   if [[ -d "$bundle" ]]; then
     echo "Opening $(basename "$file") with $app"
     open -a "$bundle" "$file"
     exit $?
   fi
 done
done
echo "No supported installed desktop application found for .$ext" >&2
exit 1

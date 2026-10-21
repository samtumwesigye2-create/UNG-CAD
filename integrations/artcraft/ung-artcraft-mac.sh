#!/usr/bin/env bash
# UNG ArtCraft local launcher. Does not install, modify, or grant privileges.
set -euo pipefail
apps=(PhotoCraft VectorCraft FilmCraft LightCraft PdfCraft EffectCraft DesignCraft FigCraft WordCraft SoundCraft DeckCraft CADCraft GridCraft)
usage(){ printf 'Usage: %s list | open APP | reveal APP\n' "$0"; }
resolve(){
 local name="$1" root path
 for root in /Applications "$HOME/Applications"; do
   path="$root/$name.app"
   if [[ -d "$path" ]]; then printf '%s\n' "$path"; return 0; fi
 done
 return 1
}
known(){
 local item
 for item in "${apps[@]}"; do [[ "$item" == "$1" ]] && return 0; done
 return 1
}
cmd="${1:-list}"
case "$cmd" in
 list)
   for name in "${apps[@]}"; do
     if path="$(resolve "$name")"; then printf 'FOUND     %-16s %s\n' "$name" "$path"; else printf 'NOT FOUND %s\n' "$name"; fi
   done
   ;;
 open|reveal)
   name="${2:-}"
   if ! known "$name"; then echo "Unknown app: $name" >&2; usage >&2; exit 2; fi
   if ! path="$(resolve "$name")"; then echo "Not installed in standard Applications locations: $name" >&2; exit 1; fi
   if [[ "$cmd" == open ]]; then open -a "$path"; else open -R "$path"; fi
   ;;
 *) usage >&2; exit 2 ;;
esac

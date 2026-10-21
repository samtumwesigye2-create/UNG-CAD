#!/usr/bin/env bash
# UNG ArtCraft Mac app adapter: discover, launch, open user-selected project files.
# No sudo, installation, remote control, arbitrary shell commands, or network listener.
set -euo pipefail
apps=(PhotoCraft VectorCraft FilmCraft LightCraft PdfCraft EffectCraft DesignCraft FigCraft WordCraft SoundCraft DeckCraft CADCraft GridCraft)
usage(){ printf 'Usage: %s list | open APP | reveal APP | open-file APP FILE\n' "$0"; }
known(){ local a; for a in "${apps[@]}"; do [[ "$a" == "$1" ]] && return 0; done; return 1; }
resolve(){
 local name="$1" root path
 for root in /Applications "$HOME/Applications"; do
   path="$root/$name.app"
   if [[ -d "$path" ]]; then printf '%s\n' "$path"; return 0; fi
 done
 return 1
}
cmd="${1:-list}"
case "$cmd" in
 list)
   for name in "${apps[@]}"; do
     if path="$(resolve "$name")"; then printf 'FOUND     %-16s %s\n' "$name" "$path"; else printf 'NOT FOUND %s\n' "$name"; fi
   done
   ;;
 open|reveal|open-file)
   name="${2:-}"
   if ! known "$name"; then echo "Unknown app: $name" >&2; usage >&2; exit 2; fi
   if ! path="$(resolve "$name")"; then echo "Not found in standard Applications locations: $name" >&2; exit 1; fi
   if [[ "$cmd" == "open" ]]; then open -a "$path"
   elif [[ "$cmd" == "reveal" ]]; then open -R "$path"
   else
     file="${3:-}"
     if [[ -z "$file" || ! -f "$file" ]]; then echo "File not found: $file" >&2; exit 2; fi
     # Pass an existing local file as a single argument; never interpret it as shell code.
     open -a "$path" -- "$file"
   fi
   ;;
 *) usage >&2; exit 2 ;;
esac

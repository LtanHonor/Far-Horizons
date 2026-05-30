#!/bin/bash
set -e
mkdir -p /tmp/fhccwrap
cat > /tmp/fhccwrap/cc <<'EOF'
#!/bin/sh
exec /usr/bin/gcc -std=gnu89 -Wno-error "$@"
EOF
chmod +x /tmp/fhccwrap/cc

PATH=/tmp/fhccwrap:$PATH make -f mk.newgal
PATH=/tmp/fhccwrap:$PATH make -f mk.mho
PATH=/tmp/fhccwrap:$PATH make -f mk.home.auto
PATH=/tmp/fhccwrap:$PATH make -f mk.listgal
PATH=/tmp/fhccwrap:$PATH make -f mk.addsp.auto
PATH=/tmp/fhccwrap:$PATH make -f mk.finish
PATH=/tmp/fhccwrap:$PATH make -f mk.report
PATH=/tmp/fhccwrap:$PATH make -f mk.mapprint
PATH=/tmp/fhccwrap:$PATH make -f mk.turn
PATH=/tmp/fhccwrap:$PATH make -f mk.no
PATH=/tmp/fhccwrap:$PATH make -f mk.combat
PATH=/tmp/fhccwrap:$PATH make -f mk.pre
PATH=/tmp/fhccwrap:$PATH make -f mk.jump
PATH=/tmp/fhccwrap:$PATH make -f mk.pro
PATH=/tmp/fhccwrap:$PATH make -f mk.post
PATH=/tmp/fhccwrap:$PATH make -f mk.loc
PATH=/tmp/fhccwrap:$PATH make -f mk.stats

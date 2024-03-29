#!/bin/bash
set -e
set -x

# run isort recursively
# isort -rc .

# Update pre-commit
pre-commit autoupdate
#run pre-commit
pre-commit run -a

# bash scripts/test.sh --cov-report=html ${@}
# python3 -m pytest
# python3 -m pytest -v -s # verbose
python3 -m pytest
# modify path for
sed -i "s/<source>\/workspace\/src<\/source>/<source>\/github\/workspace\/src<\/source>/g" /workspace/src/coverage.xml
# create coverage-badge
coverage-badge -o ../coverage.svg -f

# generate flake8 report
flake8 --tee . > flake8_report/report.txt


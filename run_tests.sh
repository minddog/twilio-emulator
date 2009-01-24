#!/bin/bash
TWILIO_SRC="/home/minddog/twilio-emulator/"
TWML_EMU="$TWILIO_SRC/twilio-emulator.py"

TESTS="multi_number.xml gather.xml pause.xml"

echo "Running tests..."

if [ "$1x" != "x" ]; then
    $TWML_EMU "file://$TWILIO_SRC/tests/$1";
    exit
fi

for test in $TESTS; do
    $TWML_EMU "file://$TWILIO_SRC/tests/$test";
done;
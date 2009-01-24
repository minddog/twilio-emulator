#!/bin/bash
TWILIO_SRC="/home/minddog/twilio-emulator/"
TWML_EMU="$TWILIO_SRC/twilio-emulator.py"

TESTS="multi_number.xml gather.xml"

echo "Running tests..."
for test in $TESTS; do
    $TWML_EMU "file://$TWILIO_SRC/tests/$test";
done;
#!/bin/sh
TWILIO_SRC="/home/minddog/twilio-emulator/"
TWML_EMU="$TWILIO_SRC/twilio-emulator.py"

echo "Running tests..."
$TWML_EMU "file://$TWILIO_SRC/tests/multi_number.xml"
"""Log the Arduino CSV to a file. Usage: python3 tools/log_serial.py /dev/cu.usbmodem1101 run1.csv
Needs: pip install pyserial  (only on the logging laptop). Close the Arduino Serial Monitor first. Ctrl-C to stop.
Then upload run1.csv in the app, tab 4 -> Upload CSV."""
import sys, time, serial
port, out = sys.argv[1], sys.argv[2]
with serial.Serial(port, 115200, timeout=1) as ser, open(out, "a", buffering=1) as f:
    time.sleep(2)                       # opening the port resets UNO/Nano; wait for boot + calibration
    ser.reset_input_buffer()
    f.write("t,roll,pitch\n") if f.tell() == 0 else None
    while True:
        line = ser.readline().decode("ascii", "ignore").strip()
        if line.count(",") == 2 and not line.startswith("t"):
            try:
                [float(x) for x in line.split(",")]
                f.write(line + "\n")
            except ValueError:
                pass                    # drop garbled partial lines

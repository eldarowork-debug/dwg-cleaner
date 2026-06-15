# DWG Cleaner

A Python utility to simplify AutoCAD DWG files by converting spline-based geometry to polylines and removing short line segments.

## Overview

`Clean-DWG.py` processes DWG files using:

- `ODA File Converter` to convert DWG ↔ DXF
- `ezdxf` to read, analyze, and rewrite DXF entities

The script converts:

- `SPLINE` entities to `LWPOLYLINE`
- `ARC` entities to polylines
- `ELLIPSE` entities to closed polylines
- optional simplification of existing polylines and short lines

It preserves layer and color attributes when converting geometry.

## Requirements

- Python 3
- `ezdxf`
- ODA File Converter installed on Windows

Suggested install:

```powershell
python -m pip install -r requirements.txt
```

If `ezdxf` is not installed, the script exits with an error and prints:

```text
ERROR: ezdxf not installed
Install with: pip install ezdxf
```

## Usage

```powershell
python Clean-DWG.py <input_folder> [options]
```

### Required argument

- `input_folder` - Folder containing `.dwg` files to process

### Common options

- `-o, --output` : Output folder (default: `input_folder/PySimplified/<timestamp>`)
- `-i, --in-place` : Process files in-place
- `-b, --backup` : Create `.bak` backup files when using `--in-place`
- `--clean-names` : Keep clean output file names instead of prefixed names
- `--keep-temp` : Keep temporary files for debugging
- `--oda-path` : Specify the ODA File Converter executable path
- `-P, --profiler` : Enable profiler output

### Spline and curve options

- `--spline-method {adaptive,fixed,tolerance}` : Spline flattening method (default: adaptive)
- `--spline-segments <int>` : Number of spline segments for fixed flattening (default: 2)
- `--spline-tolerance <float>` : Spline deviation tolerance (default: 0.9)
- `--ellipse-segments <int>` : Segments for ellipse conversion (default: 16)
- `--arc-segments <int>` : Fixed number of segments for arc flattening
- `--arc-segment-angle <float>` : Maximum angle per arc segment in degrees (default: 30.0)

### Simplification options

- `--min-line-length <float>` : Remove line segments shorter than this length (default: 0)
- `--simplify-existing` : Simplify existing polylines by removing short segments
- `--keep-short-segments` : Keep short line segments instead of removing them

## Example commands

Process a folder and write results to a new output directory:

```powershell
python Clean-DWG.py "C:\Projects\dwg_input"
```

Process in-place and keep backups:

```powershell
python Clean-DWG.py "C:\Projects\dwg_input" --in-place --backup
```

Convert splines with a fixed number of segments and remove short lines:

```powershell
python Clean-DWG.py "C:\Projects\dwg_input" --spline-method fixed --spline-segments 10 --min-line-length 0.1
```

## Notes

- The script requires a working ODA File Converter installation. If it isn't found in common Windows locations, the script exits with an error.
- Output file names are prefixed by default with configuration values unless `--clean-names` is used.
- A configuration log file is written to the output directory for each run.

## License

No license is specified in the repository.

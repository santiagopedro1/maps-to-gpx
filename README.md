# Maps to GPX

Convert a Google Maps directions URL to a road-following GPX file.

## Description

This tool takes a Google Maps directions URL and converts it into a GPX (GPS Exchange Format) file that follows the road route. It uses the Google Directions API to fetch detailed route coordinates and generates a GPX track suitable for GPS devices or mapping software.

## Requirements

- Python 3.14 or higher
- Google Maps API key (Directions API enabled)

## Installation

1. Clone or download this repository.
2. Install dependencies:

   Using uv (recommended):

   ```bash
   uv sync
   ```

   Or using pip with requirements.txt:

   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. Obtain a Google Maps API key from the [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the Directions API for your project.
2. Create a `.env` file in the project directory:

   ```
   MAPS_API_KEY=your_api_key_here
   ```

## Usage

```bash
python main.py "<google_maps_url>" [output.gpx] [options]
```

### Arguments

- `url`: The Google Maps directions URL (required)
- `output`: Output GPX file path (optional, default: `route.gpx`)

### Options

- `--mode`: Travel mode - `driving`, `walking`, `bicycling`, or `transit` (default: `driving`)
- `--name`: Track name in the GPX file (default: "My Route")

## Examples

### Basic usage

```bash
python main.py "https://www.google.com/maps/dir/Seattle,+WA/San+Francisco,+CA"
```

This creates `route.gpx` with the driving route from Seattle to San Francisco.

### With custom output and options

```bash
python main.py "https://www.google.com/maps/dir/New+York,+NY/Boston,+MA/Providence,+RI" my_trip.gpx --mode walking --name "East Coast Walk"
```

This creates `my_trip.gpx` with a walking route through the waypoints, named "East Coast Walk".

## Supported URL Formats

The script supports both old and new Google Maps URL formats:

- Classic: `https://www.google.com/maps/dir/Origin/Destination`
- New API: `https://www.google.com/maps/dir/?api=1&origin=...&destination=...&waypoints=...`

## License

[MIT License](LICENSE)
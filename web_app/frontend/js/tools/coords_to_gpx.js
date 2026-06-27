/**
 * Coordinates to GPX Tool
 * 
 * Converts user-entered coordinate pairs to a GPX file in route (<rte>) format.
 * All processing happens on the frontend; download is triggered via Blob.
 */

window.CoordsToGpx = {
  state: {
    routeName: '',
    coordinates: [],
  },

  /**
   * Initialize the tool - attach event listeners and set up UI
   */
  init() {
    const downloadBtn = document.getElementById('gpx_download_btn');
    const clearBtn = document.getElementById('gpx_clear_btn');
    const routeNameInput = document.getElementById('gpx_route_name');
    const coordinatesInput = document.getElementById('gpx_coordinates');

    downloadBtn?.addEventListener('click', () => this.handleDownload());
    clearBtn?.addEventListener('click', () => this.handleClear());

    // Optional: restore from localStorage if available
    const saved = localStorage.getItem('coords_to_gpx_state');
    if (saved) {
      try {
        this.state = JSON.parse(saved);
        routeNameInput.value = this.state.routeName;
        coordinatesInput.value = this.state.coordinates.map(c => `${c.lat},${c.lon}`).join('\n');
      } catch (e) {
        console.warn('Failed to restore saved state:', e);
      }
    }

    // Auto-save on input change
    routeNameInput?.addEventListener('change', () => this.saveState());
    coordinatesInput?.addEventListener('change', () => this.saveState());
  },

  /**
   * Save current state to localStorage
   */
  saveState() {
    const routeName = document.getElementById('gpx_route_name')?.value || '';
    const coordinatesText = document.getElementById('gpx_coordinates')?.value || '';

    this.state.routeName = routeName;
    this.state.coordinates = this.parseCoordinates(coordinatesText);

    try {
      localStorage.setItem('coords_to_gpx_state', JSON.stringify(this.state));
    } catch (e) {
      console.warn('Failed to save state to localStorage:', e);
    }
  },

  /**
   * Parse coordinate string into array of {lat, lon} objects
   * @param {string} text - Multiline text with comma-separated coords
   * @returns {Array} Array of {lat, lon} objects
   */
  parseCoordinates(text) {
    return text
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .map((line, index) => {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length !== 2) {
          throw new Error(`Line ${index + 1}: Expected "lat,lon", got "${line}"`);
        }

        const lat = parseFloat(parts[0]);
        const lon = parseFloat(parts[1]);

        if (isNaN(lat) || isNaN(lon)) {
          throw new Error(`Line ${index + 1}: Invalid coordinates "${line}" (must be numeric)`);
        }

        if (lat < -90 || lat > 90) {
          throw new Error(`Line ${index + 1}: Latitude out of range: ${lat} (must be -90 to 90)`);
        }

        if (lon < -180 || lon > 180) {
          throw new Error(`Line ${index + 1}: Longitude out of range: ${lon} (must be -180 to 180)`);
        }

        return { lat, lon };
      });
  },

  /**
   * Build a complete GPX document string
   * @param {string} routeName - Name of the route
   * @param {Array} coordinates - Array of {lat, lon} objects
   * @returns {string} Valid GPX XML
   */
  buildGPX(routeName, coordinates) {
    const timestamp = new Date().toISOString();

    // Build route points
    const routePoints = coordinates
      .map((coord, index) => {
        return `    <rtept lat="${coord.lat}" lon="${coord.lon}">
      <name>Point ${index + 1}</name>
      <desc>Waypoint ${index + 1}</desc>
    </rtept>`;
      })
      .join('\n');

    // Build complete GPX document
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"
     creator="Pokémon GO Mapping Web App"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1
     http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>${this.escapeXML(routeName)}</name>
    <desc>Route created by Pokémon GO Mapping Web App</desc>
    <time>${timestamp}</time>
  </metadata>
  <rte>
    <name>${this.escapeXML(routeName)}</name>
${routePoints}
  </rte>
</gpx>`;

    return gpx;
  },

  /**
   * Escape special XML characters
   * @param {string} text
   * @returns {string}
   */
  escapeXML(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  },

  /**
   * Show a message to the user
   * @param {string} message - The message text
   * @param {string} type - 'error' or 'success'
   */
  showMessage(message, type = 'error') {
    const messageEl = document.getElementById('gpx_message');
    if (!messageEl) return;

    messageEl.textContent = message;
    messageEl.className = `form-message form-message-${type}`;
    messageEl.style.display = 'block';

    if (type === 'success') {
      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    }
  },

  /**
   * Handle Download button click
   */
  handleDownload() {
    try {
      this.saveState();

      const routeName = document.getElementById('gpx_route_name')?.value?.trim();
      if (!routeName) {
        this.showMessage('Please enter a route name', 'error');
        return;
      }

      const coordinatesText = document.getElementById('gpx_coordinates')?.value?.trim();
      if (!coordinatesText) {
        this.showMessage('Please enter at least one coordinate pair', 'error');
        return;
      }

      // Parse and validate coordinates
      const coordinates = this.parseCoordinates(coordinatesText);
      if (coordinates.length === 0) {
        this.showMessage('No valid coordinates found', 'error');
        return;
      }

      // Build GPX
      const gpxContent = this.buildGPX(routeName, coordinates);

      // Create download
      const blob = new Blob([gpxContent], { type: 'application/gpx+xml' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${routeName}.gpx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      this.showMessage(`GPX file "${routeName}.gpx" downloaded successfully!`, 'success');
    } catch (error) {
      console.error('Error generating GPX:', error);
      this.showMessage(`Error: ${error.message}`, 'error');
    }
  },

  /**
   * Handle Clear button click
   */
  handleClear() {
    document.getElementById('gpx_route_name').value = '';
    document.getElementById('gpx_coordinates').value = '';
    document.getElementById('gpx_message').style.display = 'none';
    this.state = { routeName: '', coordinates: [] };
    localStorage.removeItem('coords_to_gpx_state');
  },
};

// Auto-initialize when tool is shown
document.addEventListener('toolshow', (e) => {
  if (e.detail?.toolId === 'coords_to_gpx') {
    CoordsToGpx.init();
  }
});

// Initialize on page load if tool might be visible
document.addEventListener('DOMContentLoaded', () => {
  // Only init if the tool container exists
  if (document.getElementById('tool_coords_to_gpx')) {
    CoordsToGpx.init();
  }
});

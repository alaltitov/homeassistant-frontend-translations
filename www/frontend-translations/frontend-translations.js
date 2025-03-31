/**
 * Frontend Translations Integration - Client Side
 * 
 * Handles automatic synchronization of translation metadata between 
 * Home Assistant frontend and backend.
 * 
 * @author alaltitov
 * @fileoverview Manages translation metadata updates and WebSocket communication
 * @version 1.0.0
 */

/**
 * Stores translation metadata via WebSocket API
 * @param {Object} hass - Home Assistant connection object
 * @param {Object} hass.translationMetadata - Translation metadata from frontend
 * @param {Object} hass.connection - WebSocket connection handler
 */
function storeTranslations(hass) {
  if (hass.translationMetadata?.translations) {
    const connection = hass.connection || hass._connection;
    if (connection?.sendMessagePromise) {
      connection.sendMessagePromise({
        type: "frontend_translations/store_metadata",
        metadata: hass.translationMetadata.translations
      }).catch(error => {
        console.error("[Frontend Translations] Error storing metadata:", error);
      });
    }
  }
}

/**
 * Initializes translation tracking logic
 * - Waits for Home Assistant core element
 * - Sets up metadata change detection
 */
function initFrontendTranslations() {
  const waitForHass = setInterval(() => {
    const homeAssistant = document.querySelector("home-assistant");
    
    if (homeAssistant?.hass) {
      clearInterval(waitForHass);
      const hass = homeAssistant.hass;

      // Initial metadata sync
      setTimeout(() => storeTranslations(hass), 5000);

      // Metadata change detection
      let lastHash = JSON.stringify(hass.translationMetadata);
      setInterval(() => {
        if (homeAssistant?.hass) {
          const currentHash = JSON.stringify(homeAssistant.hass.translationMetadata);
          if (currentHash !== lastHash) {
            lastHash = currentHash;
            storeTranslations(homeAssistant.hass);
          }
        }
      }, 60000);
    }
  }, 1000);
}

// Event Listeners
window.addEventListener('load', () => {
  setTimeout(initFrontendTranslations, 3000);
});

window.addEventListener('location-changed', () => {
  setTimeout(() => {
    const homeAssistant = document.querySelector("home-assistant");
    if (homeAssistant?.hass) {
      storeTranslations(homeAssistant.hass);
    }
  }, 2000);
});

document.addEventListener("hass-ready", () => {
  setTimeout(() => {
    const homeAssistant = document.querySelector("home-assistant");
    if (homeAssistant?.hass) {
      storeTranslations(homeAssistant.hass);
    }
  }, 5000);
});
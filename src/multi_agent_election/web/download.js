"use strict";

// Keep the latest prepared file available for a direct user-initiated retry.
function createDownloadManager(container, environment = {document, URL, setTimeout: (callback, delay) => setTimeout(callback, delay)}) {
  let previousUrl = null;
  return {
    download(blob, filename, description) {
      const url = environment.URL.createObjectURL(blob);
      const link = environment.document.createElement("a");
      link.href = url; link.download = filename;
      link.textContent = `Save ${filename} (${description})`;
      container.replaceChildren(link);
      // A previously clicked download may still be consuming its object URL.
      if (previousUrl !== null) {
        const retiredUrl = previousUrl;
        environment.setTimeout(() => environment.URL.revokeObjectURL(retiredUrl), 60000);
      }
      previousUrl = url;
      link.click();
    },
  };
}

if (typeof module !== "undefined" && module.exports) module.exports = {createDownloadManager};

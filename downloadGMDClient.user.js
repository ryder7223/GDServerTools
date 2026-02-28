// ==UserScript==
// @name         GD Level Downloader
// @namespace    https://github.com/Ryder7223
// @version      1.0.2
// @author       Ryder7223
// @description  Makes Boomlings requests from the user's browser and sends results to the downloader page.
// @match        *://*/*downloadGMDClient*
// @match        file:///*downloadGMDClient*
// @grant        GM_xmlhttpRequest
// @connect      www.boomlings.com
// @license      CC BY-ND 4.0; You may use this script but not modify or distribute modified versions.
// @downloadURL  https://update.greasyfork.org/scripts/567822/GD%20Level%20Downloader.user.js
// @updateURL    https://update.greasyfork.org/scripts/567822/GD%20Level%20Downloader.meta.js
// ==/UserScript==

(function () {
  "use strict";

  // Let the page detect that the userscript is installed.
  try {
    // Tampermonkey sandbox: unsafeWindow exists in most setups, but not always.
    // If unsafeWindow doesn't exist, setting window flag still helps in some managers.
    // eslint-disable-next-line no-undef
    (typeof unsafeWindow !== "undefined" ? unsafeWindow : window).__boomlingsUserscriptEnabled = true;
  } catch (_) {
    window.__boomlingsUserscriptEnabled = true;
  }

  window.addEventListener("message", (event) => {
    const msg = event?.data;
    if (!msg || msg.type !== "boomlingsDownload" || !msg.levelID) return;

    const levelID = String(msg.levelID).trim();
    if (!levelID) return;

    GM_xmlhttpRequest({
      method: "POST",
      url: "http://www.boomlings.com/database/downloadGJLevel22.php",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      data: `secret=${encodeURIComponent("Wmfd2893gb7")}&levelID=${encodeURIComponent(levelID)}`,
      timeout: 15000,
      onload: (resp) => {
        window.postMessage(
          {
            type: "boomlingsDownloadResult",
            levelID,
            ok: true,
            status: resp.status,
            text: resp.responseText ?? ""
          },
          "*"
        );
      },
      ontimeout: () => {
        window.postMessage(
          { type: "boomlingsDownloadResult", levelID, ok: false, error: "Request timed out" },
          "*"
        );
      },
      onerror: () => {
        window.postMessage(
          { type: "boomlingsDownloadResult", levelID, ok: false, error: "Network error" },
          "*"
        );
      }
    });
  });
})();

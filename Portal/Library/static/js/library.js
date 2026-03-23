(function () {
    "use strict";

    // ── State ────────────────────────────────────────────────────────

    const state = {
        books: [],
        videos: [],
        activeTab: "books",
        scanner: null,
    };

    // ── DOM refs ─────────────────────────────────────────────────────

    const $ = (id) => document.getElementById(id);
    const cardGrid = $("card-grid");
    const emptyState = $("empty-state");
    const searchInput = $("search-input");
    const scanFab = $("scan-fab");
    const itemCount = $("item-count");
    const booksCount = $("books-count");
    const videosCount = $("videos-count");
    const scannerOverlay = $("scanner-overlay");
    const selectionModal = $("selection-modal");
    const selectionOptions = $("selection-options");
    const manualModal = $("manual-modal");
    const manualForm = $("manual-form");
    const loadingOverlay = $("loading");
    const toastContainer = $("toast-container");

    // ── Data loading ─────────────────────────────────────────────────

    async function loadLibrary(type) {
        try {
            const res = await fetch(`/api/${type}`);
            if (!res.ok) throw new Error(res.statusText);
            state[type] = await res.json();
            updateCounts();
            if (type === state.activeTab) renderCards(state[type]);
        } catch (err) {
            showToast("Failed to load " + type, "error");
        }
    }

    function updateCounts() {
        booksCount.textContent = `(${state.books.length})`;
        videosCount.textContent = `(${state.videos.length})`;
        const active = state[state.activeTab];
        itemCount.textContent = active.length
            ? `${active.length} ${state.activeTab}`
            : "";
    }

    // ── Rendering ────────────────────────────────────────────────────

    function renderCards(data) {
        cardGrid.innerHTML = "";
        emptyState.style.display = data.length ? "none" : "block";

        data.forEach((item) => {
            const card = document.createElement("div");
            card.className = "card";

            const isBook = state.activeTab === "books";
            const coverSrc = isBook ? item.cover_url : item.cover_base64;
            const icon = isBook ? "fa-book" : "fa-film";

            if (coverSrc) {
                const img = document.createElement("img");
                img.className = "card-cover";
                img.src = coverSrc;
                img.alt = item.title;
                img.loading = "lazy";
                img.onerror = function () {
                    this.replaceWith(makePlaceholder(icon));
                };
                card.appendChild(img);
            } else {
                card.appendChild(makePlaceholder(icon));
            }

            const info = document.createElement("div");
            info.className = "card-info";

            const title = document.createElement("div");
            title.className = "card-title";
            title.textContent = item.title;
            info.appendChild(title);

            const subtitle = document.createElement("div");
            subtitle.className = "card-subtitle";
            if (isBook) {
                subtitle.textContent = [item.author, item.year]
                    .filter(Boolean)
                    .join(" · ");
            } else {
                subtitle.textContent = item.year || "";
            }
            info.appendChild(subtitle);

            if (!isBook && item.type) {
                const badge = document.createElement("span");
                badge.className = "card-badge";
                badge.textContent = item.type;
                info.appendChild(badge);
            }

            card.appendChild(info);
            cardGrid.appendChild(card);
        });
    }

    function makePlaceholder(iconClass) {
        const div = document.createElement("div");
        div.className = "card-placeholder";
        div.innerHTML = `<i class="fas ${iconClass}"></i>`;
        return div;
    }

    // ── Search ───────────────────────────────────────────────────────

    let searchTimer = null;

    function searchFilter(query) {
        const data = state[state.activeTab];
        if (!query.trim()) {
            renderCards(data);
            return;
        }
        const q = query.toLowerCase();
        const filtered = data.filter((item) => {
            const fields = [item.title, item.author, item.isbn, String(item.year || "")];
            return fields.some((f) => f && f.toLowerCase().includes(q));
        });
        renderCards(filtered);
    }

    // ── Tabs ─────────────────────────────────────────────────────────

    function switchTab(type) {
        state.activeTab = type;
        document.querySelectorAll(".tab").forEach((t) => {
            t.classList.toggle("active", t.dataset.tab === type);
        });
        scanFab.style.display = type === "books" ? "flex" : "none";
        searchInput.value = "";
        updateCounts();
        renderCards(state[type]);
    }

    // ── Scanner ──────────────────────────────────────────────────────

    const BARCODE_FORMATS = [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.UPC_A,
        Html5QrcodeSupportedFormats.UPC_E,
        Html5QrcodeSupportedFormats.CODE_128,
    ];

    function initScanner() {
        scannerOverlay.style.display = "flex";

        // Try live camera first, but don't block if unavailable
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const html5Qr = new Html5Qrcode("scanner-region", {
                formatsToSupport: BARCODE_FORMATS,
            });
            state.scanner = html5Qr;

            // Responsive qrbox: 80% of scanner region width, capped at 250px
            const regionWidth = $("scanner-region").clientWidth;
            const qrboxSize = Math.min(250, Math.floor(regionWidth * 0.8));

            html5Qr
                .start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: qrboxSize },
                    onScanSuccess,
                    () => {} // ignore per-frame scan misses
                )
                .catch((err) => {
                    console.warn("Live scanner failed, use photo instead:", err);
                    // Don't close overlay — user can still use "Scan from photo"
                    const msg = err.name || String(err);
                    if (msg.includes("NotAllowedError")) {
                        showToast("Camera denied — use 'Scan from photo' below", "error");
                    } else {
                        showToast("Camera unavailable — use 'Scan from photo' below", "error");
                    }
                    state.scanner = null;
                });
        } else {
            showToast("No live camera — use 'Scan from photo'", "error");
        }
    }

    function scanFromFile(file) {
        if (!file) return;
        const html5Qr = new Html5Qrcode("scanner-region", {
            formatsToSupport: BARCODE_FORMATS,
        });
        html5Qr
            .scanFile(file, /* showImage */ false)
            .then(onScanSuccess)
            .catch(() => {
                showToast("No barcode found in photo — try again", "error");
            });
    }

    function stopScanner() {
        if (state.scanner) {
            state.scanner
                .stop()
                .catch(() => {})
                .finally(() => {
                    state.scanner = null;
                });
        }
        // Reset file input so the same photo can be re-selected
        const fileInput = $("scan-file-input");
        if (fileInput) fileInput.value = "";
        scannerOverlay.style.display = "none";
    }

    function onScanSuccess(decodedText) {
        stopScanner();

        const isbn = decodedText.trim();
        if (state.books.some((b) => b.isbn === isbn)) {
            showToast("Already in your library!", "error");
            return;
        }

        fetchBookMetadata(isbn);
    }

    // ── Book metadata lookup ─────────────────────────────────────────

    async function fetchBookMetadata(isbn) {
        loadingOverlay.style.display = "flex";

        try {
            const [googleRes, olRes] = await Promise.allSettled([
                fetch(
                    `https://www.googleapis.com/books/v1/volumes?q=isbn:${isbn}`
                ).then((r) => r.json()),
                fetch(`https://openlibrary.org/isbn/${isbn}.json`).then((r) =>
                    r.json()
                ),
            ]);

            const options = compileOptions(
                googleRes.status === "fulfilled" ? googleRes.value : null,
                olRes.status === "fulfilled" ? olRes.value : null,
                isbn
            );

            loadingOverlay.style.display = "none";

            if (options.length === 0) {
                showToast("No results found — enter details manually", "error");
                openManualModal(isbn);
            } else if (options.length === 1) {
                showSelectionModal(options);
            } else {
                showSelectionModal(options);
            }
        } catch {
            loadingOverlay.style.display = "none";
            showToast("Lookup failed — enter details manually", "error");
            openManualModal(isbn);
        }
    }

    function compileOptions(google, openLib, isbn) {
        const options = [];

        // Google Books results
        if (google && google.items) {
            google.items.forEach((item) => {
                const v = item.volumeInfo || {};
                const thumb = v.imageLinks
                    ? (v.imageLinks.thumbnail || v.imageLinks.smallThumbnail || "").replace(
                          "http:",
                          "https:"
                      )
                    : "";
                options.push({
                    isbn: isbn,
                    title: v.title || "",
                    author: (v.authors || []).join(", "),
                    publisher: v.publisher || "",
                    year: (v.publishedDate || "").substring(0, 4),
                    page_count: v.pageCount || null,
                    cover_url: thumb,
                    source: "google",
                });
            });
        }

        // Open Library result
        if (openLib && openLib.title) {
            const olCover = `https://covers.openlibrary.org/b/isbn/${isbn}-L.jpg`;
            options.push({
                isbn: isbn,
                title: openLib.title || "",
                author: "", // OL author needs a follow-up fetch; left blank for now
                publisher: (openLib.publishers || []).join(", "),
                year: (openLib.publish_date || "").slice(-4),
                page_count: openLib.number_of_pages || null,
                cover_url: olCover,
                source: "openlibrary",
            });
        }

        // Deduplicate by title+publisher (case-insensitive)
        const seen = new Set();
        return options.filter((o) => {
            const key = (o.title + "|" + o.publisher).toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    // ── Selection modal ──────────────────────────────────────────────

    function showSelectionModal(options) {
        selectionOptions.innerHTML = "";

        options.forEach((opt) => {
            const btn = document.createElement("button");
            btn.className = "option-card";

            const thumbHtml = opt.cover_url
                ? `<img class="option-thumb" src="${opt.cover_url}" alt="">`
                : `<div class="option-thumb" style="display:flex;align-items:center;justify-content:center;color:#7c8aff;"><i class="fas fa-book"></i></div>`;

            btn.innerHTML = `
                ${thumbHtml}
                <div class="option-details">
                    <div class="option-title">${esc(opt.title)}</div>
                    <div class="option-meta">${esc(opt.author)}</div>
                    <div class="option-meta">${esc(opt.publisher)} ${esc(opt.year)}</div>
                </div>
            `;

            btn.addEventListener("click", () => {
                closeModal("selection-modal");
                saveBook(opt);
            });

            selectionOptions.appendChild(btn);
        });

        selectionModal.style.display = "flex";
    }

    // ── Save book ────────────────────────────────────────────────────

    async function saveBook(bookObj) {
        // Strip the internal 'source' field before saving
        const toSave = { ...bookObj };
        delete toSave.source;

        try {
            const res = await fetch("/api/books", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(toSave),
            });

            if (res.status === 201) {
                const saved = await res.json();
                state.books.push(saved);
                updateCounts();
                renderCards(state.books);
                showToast("Added to library!");
            } else if (res.status === 409) {
                showToast("Already in your library!", "error");
            } else {
                const err = await res.json();
                showToast(err.error || "Failed to save", "error");
            }
        } catch {
            showToast("Network error — try again", "error");
        }
    }

    // ── Manual entry modal ───────────────────────────────────────────

    function openManualModal(isbn) {
        $("manual-isbn").value = isbn || "";
        $("manual-title").value = "";
        $("manual-author").value = "";
        $("manual-publisher").value = "";
        $("manual-year").value = "";
        manualModal.style.display = "flex";
    }

    $("manual-search-btn").addEventListener("click", () => {
        const isbn = $("manual-isbn").value.trim();
        if (isbn) {
            closeModal("manual-modal");
            fetchBookMetadata(isbn);
        } else {
            showToast("Enter an ISBN first", "error");
        }
    });

    manualForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = $("manual-title").value.trim();
        if (!title) {
            showToast("Title is required", "error");
            return;
        }

        const book = {
            isbn: $("manual-isbn").value.trim() || null,
            title: title,
            author: $("manual-author").value.trim(),
            publisher: $("manual-publisher").value.trim(),
            year: $("manual-year").value.trim(),
            cover_url: "",
            page_count: null,
        };

        closeModal("manual-modal");
        await saveBook(book);
    });

    // ── Modal helpers ────────────────────────────────────────────────

    function closeModal(id) {
        $(id).style.display = "none";
    }

    document.querySelectorAll("[data-close]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.close;
            closeModal(target);
            if (target === "scanner-overlay") stopScanner();
        });
    });

    // ── Toast ────────────────────────────────────────────────────────

    function showToast(message, type) {
        const el = document.createElement("div");
        el.className = "toast" + (type === "error" ? " error" : "");
        el.textContent = message;
        toastContainer.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    }

    // ── Utilities ────────────────────────────────────────────────────

    function esc(str) {
        if (!str) return "";
        const el = document.createElement("span");
        el.textContent = str;
        return el.innerHTML;
    }

    // ── Init ─────────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", () => {
        loadLibrary("books");
        loadLibrary("videos");

        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => searchFilter(searchInput.value), 150);
        });

        document.querySelectorAll(".tab").forEach((tab) => {
            tab.addEventListener("click", () => switchTab(tab.dataset.tab));
        });

        scanFab.addEventListener("click", initScanner);

        $("scan-file-input").addEventListener("change", (e) => {
            scanFromFile(e.target.files[0]);
        });

        $("manual-entry-link").addEventListener("click", () => {
            stopScanner();
            openManualModal("");
        });
    });
})();

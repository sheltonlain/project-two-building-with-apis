// Typeable filters: turns <select data-combobox> into a combobox you can type into to narrow the
// list (ARIA combobox/listbox pattern). The real select stays in the form, hidden, and is what
// gets submitted, so URLs and server code don't change. Without JavaScript the plain select shows.
(() => {
  let nextId = 0;

  function enhance(select) {
    if (select._combobox) return;
    select._combobox = true;
    // A page restored from history comes back with the old (dead) combobox in front of the
    // select; replace it.
    if (select.previousElementSibling?.hasAttribute("data-combobox-ui")) {
      select.previousElementSibling.remove();
    }

    const id = `combobox-${++nextId}`;
    const blank = [...select.options].find((option) => option.value === "");
    const wrapper = document.createElement("div");
    wrapper.className = "relative";
    wrapper.setAttribute("data-combobox-ui", "");

    const input = document.createElement("input");
    input.type = "text";
    input.className = "input input-bordered";
    input.autocomplete = "off";
    input.placeholder = blank ? blank.text : "";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", `${id}-list`);

    const list = document.createElement("div");
    list.id = `${id}-list`;
    list.hidden = true;
    list.setAttribute("role", "listbox");
    list.className =
      "absolute z-20 mt-1 min-w-full w-max max-w-sm max-h-72 overflow-y-auto " +
      "rounded-box bg-base-100 p-1 shadow-lg border border-base-300";

    // One listbox row per option, with each optgroup's options under its heading.
    const items = [];
    const groups = [];
    const addOption = (option, parent) => {
      const item = document.createElement("div");
      item.id = `${id}-option-${items.length}`;
      item.setAttribute("role", "option");
      item.className = "px-3 py-1.5 rounded-field cursor-pointer";
      item.textContent = option.text;
      item._option = option;
      parent.appendChild(item);
      items.push(item);
      return item;
    };
    for (const child of select.children) {
      if (child.tagName === "OPTGROUP") {
        const group = document.createElement("div");
        group.setAttribute("role", "group");
        group.setAttribute("aria-labelledby", `${id}-group-${groups.length}`);
        const heading = document.createElement("div");
        heading.id = `${id}-group-${groups.length}`;
        heading.setAttribute("role", "presentation");
        heading.className = "px-3 pt-2 pb-1 text-xs font-semibold uppercase opacity-60";
        heading.textContent = child.label;
        group.appendChild(heading);
        group._items = [...child.children].map((option) => addOption(option, group));
        list.appendChild(group);
        groups.push(group);
      } else {
        addOption(child, list);
      }
    }
    const empty = document.createElement("div");
    empty.className = "px-3 py-1.5 opacity-60";
    empty.textContent = "No matches";
    empty.hidden = true;
    list.appendChild(empty);

    wrapper.append(input, list);
    // Before the select, so the surrounding <label> names the text box.
    select.before(wrapper);
    select.hidden = true;
    select.tabIndex = -1;

    let active = null;
    const visible = () => items.filter((item) => !item.hidden);
    const currentText = () => (select.value === "" ? "" : select.selectedOptions[0]?.text ?? "");
    const isOpen = () => !list.hidden;

    function setActive(item) {
      active?.classList.remove("bg-base-200");
      active = item;
      if (item) {
        item.classList.add("bg-base-200");
        input.setAttribute("aria-activedescendant", item.id);
        item.scrollIntoView({ block: "nearest" });
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function filter(query) {
      const needle = query.trim().toLowerCase();
      for (const item of items) {
        // The clear choice ("Any set") is always there.
        item.hidden =
          item._option.value !== "" && !item.textContent.toLowerCase().includes(needle);
      }
      for (const group of groups) group.hidden = group._items.every((item) => item.hidden);
      empty.hidden = visible().some((item) => item._option.value !== "");
    }

    function open() {
      if (isOpen()) return;
      for (const item of items) {
        const selected = item._option.value === select.value;
        item.setAttribute("aria-selected", String(selected));
        item.classList.toggle("font-semibold", selected);
      }
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function close() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      setActive(null);
    }

    // Closes the list and puts the current choice back in the box, discarding any typing.
    function restore() {
      close();
      input.value = currentText();
    }

    function openAll() {
      filter("");
      open();
      setActive(items.find((item) => item._option.value === select.value) ?? items[0]);
    }

    function choose(item) {
      if (select.value !== item._option.value) {
        select.value = item._option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      restore();
    }

    function move(step) {
      const shown = visible();
      if (!shown.length) return;
      const index = shown.indexOf(active);
      const next = index === -1 ? (step > 0 ? 0 : shown.length - 1) : index + step;
      setActive(shown[Math.min(Math.max(next, 0), shown.length - 1)]);
    }

    input.addEventListener("input", () => {
      filter(input.value);
      open();
      // Enter picks the first match; with the box emptied, Enter clears the filter.
      const shown = visible();
      setActive(
        input.value.trim()
          ? shown.find((item) => item._option.value !== "") ?? shown[0]
          : shown.find((item) => item._option.value === "") ?? shown[0],
      );
    });
    input.addEventListener("focus", () => input.select());
    input.addEventListener("click", () => (isOpen() ? null : openAll()));
    input.addEventListener("blur", restore);
    input.addEventListener("keydown", (event) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          if (isOpen()) move(1);
          else openAll();
          break;
        case "ArrowUp":
          event.preventDefault();
          if (isOpen()) move(-1);
          else openAll();
          break;
        case "Enter":
          // With the list closed, Enter submits the form as usual.
          if (isOpen() && active) {
            event.preventDefault();
            choose(active);
          }
          break;
        case "Escape":
          if (isOpen() || input.value !== currentText()) {
            event.preventDefault();
            restore();
          }
          break;
      }
    });
    // Keep focus in the text box while clicking the list.
    list.addEventListener("mousedown", (event) => event.preventDefault());
    list.addEventListener("click", (event) => {
      const item = event.target.closest("[role=option]");
      if (!item) return;
      // Stops the surrounding <label> from passing the click on to the text box.
      event.preventDefault();
      choose(item);
    });
    list.addEventListener("mousemove", (event) => {
      const item = event.target.closest("[role=option]");
      if (item && item !== active) setActive(item);
    });

    input.value = currentText();
  }

  const init = (root = document) => {
    if (root.matches?.("select[data-combobox]")) enhance(root);
    root.querySelectorAll?.("select[data-combobox]").forEach(enhance);
  };

  // On page load, on every HTMX swap (the search panel), and after Back restores a page.
  document.addEventListener("DOMContentLoaded", () => init());
  document.addEventListener("htmx:load", (event) => init(event.detail.elt));
  document.addEventListener("htmx:historyRestore", () => init());
})();

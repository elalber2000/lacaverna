(() => {
  const object = document.querySelector(".travel-map-object");
  const tooltip = document.querySelector(".travel-map-tooltip");
  const mapFrame = object;
  if (!object || !tooltip) return;

  let attached = false;
  const attachCountryHover = () => {
    const svg = mapFrame.contentDocument?.querySelector("svg");
    if (!svg || attached) return;
    attached = true;

    svg.querySelectorAll("path[data-country-id]").forEach(path => {
      const title = path.querySelector("title");
      if (!title) return;
      path.dataset.countryName = title.textContent.trim();
      path.setAttribute("aria-label", path.dataset.countryName);
      title.remove();
    });

    const showCountry = event => {
      const path = event.target.closest?.("path[data-country-id]");
      const title = path?.dataset.countryName;
      if (!title) return;
      const frameRect = object.getBoundingClientRect();
      const wrapperRect = object.parentElement.getBoundingClientRect();
      tooltip.textContent = title;
      tooltip.classList.toggle("is-visited", path.classList.contains("visited"));
      tooltip.style.left = `${event.clientX + frameRect.left - wrapperRect.left}px`;
      tooltip.style.top = `${event.clientY + frameRect.top - wrapperRect.top}px`;
      tooltip.hidden = false;
    };

    svg.addEventListener("pointerover", showCountry);
    svg.addEventListener("pointermove", showCountry);
    svg.addEventListener("pointerout", event => {
      if (!event.relatedTarget?.closest?.("path[data-country-id]")) {
        tooltip.hidden = true;
      }
    });
  };
  object.addEventListener("load", attachCountryHover);
  attachCountryHover();
})();

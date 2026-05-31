(function () {
  const countEl = document.getElementById("regular-attendee-count");
  const tableEl = document.querySelector("[data-regular-only]");
  const regularOnly = tableEl?.dataset.regularOnly === "1";

  function updateRegularCount(count) {
    if (countEl && typeof count === "number") {
      countEl.textContent = `${count} regular`;
    }
  }

  function setRegularButtonState(form, isRegular) {
    const hidden = form.querySelector('input[name="is_regular_attendee"]');
    const button = form.querySelector('button[type="submit"]');
    if (!hidden || !button) return;

    hidden.value = isRegular ? "0" : "1";
    button.textContent = isRegular ? "Yes" : "No";
    button.title = isRegular ? "Remove from speaker pool" : "Add to speaker pool";
    button.classList.toggle("btn-success", isRegular);
    button.classList.toggle("btn-outline-secondary", !isRegular);
  }

  document.querySelectorAll("form[data-regular-attendee-toggle]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error("Request failed");

        const data = await response.json();
        setRegularButtonState(form, data.is_regular_attendee);
        updateRegularCount(data.regular_count);

        if (regularOnly && !data.is_regular_attendee) {
          form.closest("tr")?.remove();
        }
      } catch (err) {
        console.error(err);
        form.submit();
      } finally {
        if (button) button.disabled = false;
      }
    });
  });
})();

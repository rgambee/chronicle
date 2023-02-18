function onSubmit(event) {
    const form = event.currentTarget;
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
    }
    event.currentTarget.classList.add("was-validated");
}

document.querySelectorAll(".needs-validation").forEach(
    (form) => {
        form.addEventListener("submit", onSubmit);
    },
);

function onSubmit(event) {
    const form = event.currentTarget;
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
    }
    event.currentTarget.classList.add("was-validated");
}

document.querySelectorAll(".style-validation").forEach(
    (form) => {
        form.addEventListener("submit", onSubmit);
    },
);

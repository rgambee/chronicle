// Custom date filtering based on this answer by Oli Folkerd:
// https://stackoverflow.com/a/64414478

function rangeEditor(cell, onRendered, success, cancel) {
    const startInput = document.createElement("input");
    startInput.setAttribute("type", "date");
    startInput.className = "form-control";
    const endInput = startInput.cloneNode();

    const container = document.createElement("span");
    container.appendChild(startInput);
    container.appendChild(endInput);

    function buildRange() {
        let start;
        let end;
        if (startInput.value) {
            start = new Date(startInput.value);
        }
        if (endInput.value) {
            end = new Date(endInput.value);
        }
        success(
            {
                start: start,
                end: end,
            },
        );
    }

    function onKeypress(event) {
        if (event.key === "Enter") {
            buildRange();
        }
        else if (
            event.key === "Esc" || event.key === "Backspace" || event.key === "Delete"
        ) {
            cancel();
        }
    }

    startInput.addEventListener("change", buildRange);
    startInput.addEventListener("blur", buildRange);
    startInput.addEventListener("keydown", onKeypress);
    endInput.addEventListener("change", buildRange);
    endInput.addEventListener("blur", buildRange);
    endInput.addEventListener("keydown", onKeypress);

    return container;
}

function rangeFilter(dateRange, dateValue) {
    if (!dateValue) {
        // Include empty dates by default
        return true;
    }
    dateValue = new Date(dateValue);
    if (dateRange.start) {
        if (dateRange.end) {
            return dateValue >= dateRange.start && dateValue <= dateRange.end;
        } else {
            return dateValue >= dateRange.start;
        }
    } else if (dateRange.end) {
        return dateValue <= dateRange.end;
    }
    // If neither side of range is defined, return true so all rows are included
    return true;
}

new Tabulator(
    "#entry-table",
    {
        responsiveLayout: "hide",
        columns: [
            {
                title: "Date",
                responsive: 10,
                frozen: true,
                formatter: "datetime",
                formatterParams:{
                    inputFormat:"yyyy-MM-dd",
                    outputFormat:"DD",
                },
                width: 175,
                headerFilter: rangeEditor,
                headerFilterFunc: rangeFilter,
                headerFilterLiveFilter: false,
            },
            {
                title: "Amount",
                sorter: "number",
                responsive: 10,
            },
            {
                title: "Category",
                responsive: 20,
                headerFilter: "input",
            },
            {
                title: "Tags",
                responsive: 30,
                headerFilter: "input",
            },
            {
                title: "Comment",
                responsive: 40,
                headerFilter: "input",
            },
            {
                title: "Edit",
                responsive: 50,
                formatter: "html",
            },
            {
                title: "Delete",
                responsive: 50,
                formatter: "html",
            },
        ],
    },
);

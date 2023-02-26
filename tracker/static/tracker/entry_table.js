// Custom date filtering based on this answer by Oli Folkerd:
// https://stackoverflow.com/a/64414478

function rangeEditor(cell, onRendered, success, cancel) {
    const template = document.querySelector("#id_date_range_template");
    const dateRange = template.content.cloneNode(true);
    const startInput = dateRange.querySelector("#id_date_range_start");
    const endInput = dateRange.querySelector("#id_date_range_end");
    const startClear = dateRange.querySelector("#id_date_range_start_clear");
    const endClear = dateRange.querySelector("#id_date_range_end_clear");

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

    function clear(input) {
        input.value = "";
        buildRange();
    }

    startInput.addEventListener("change", buildRange);
    startInput.addEventListener("blur", buildRange);
    startInput.addEventListener("keydown", onKeypress);
    endInput.addEventListener("change", buildRange);
    endInput.addEventListener("blur", buildRange);
    endInput.addEventListener("keydown", onKeypress);

    startClear.addEventListener("click", () => clear(startInput));
    endClear.addEventListener("click", () => clear(endInput));

    return dateRange.firstElementChild;
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
    "#id_entry_table",
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
                width: 220,
                headerFilter: rangeEditor,
                headerFilterFunc: rangeFilter,
                headerFilterLiveFilter: false,
                editor: "date",
            },
            {
                title: "Amount",
                responsive: 10,
                sorter: "number",
                editor: "number",
                editorParams: {
                    selectContents: true,
                    min: 0,
                },
            },
            {
                title: "Category",
                responsive: 20,
                headerFilter: "input",
                editor: "input",
                editorParams: {
                    selectContents: true,
                },
            },
            {
                title: "Tags",
                responsive: 30,
                headerFilter: "input",
                editor: "input",
                editorParams: {
                    selectContents: true,
                },
            },
            {
                title: "Comment",
                responsive: 40,
                headerFilter: "input",
                editor: "textarea",
                editorParams: {
                    selectContents: true,
                    shiftEnterSubmit: true,
                },
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

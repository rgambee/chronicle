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

function comparisonEditor(cell, onRendered, success) {
    const template = document.querySelector("#id_amount_comparison_template");
    const comparison = template.content.cloneNode(true);
    const comparisonSelect = comparison.querySelector("#id_amount_comparison_select");
    const amountInput = comparison.querySelector("#id_amount_filter");

    function buildComparison() {
        let filt = () => true;
        const amount = parseFloat(amountInput.value);
        if (isNaN(amount)) {
            success(filt);
            return;
        }
        if (comparisonSelect.value === "==") {
            console.log("==");
            filt = (value) => value === amount;
        } else if (comparisonSelect.value === "<=") {
            console.log("<=");
            filt = (value) => value <= amount;
        } else if (comparisonSelect.value === ">=") {
            console.log(">=");
            filt = (value) => value >= amount;
        } else {
            console.log("Returning default filter");
        }
        // If comparisonSelect.value isn't one of the above, return the default filter,
        // which matches all values.
        success(filt);
    }

    comparisonSelect.addEventListener("change", buildComparison);
    amountInput.addEventListener("input", buildComparison);

    return comparison.firstElementChild;
}

function comparisonFilter(compare, value) {
    return compare(value);
}

// Function must be bound to an instance of Tabulator
function deleteSelected() {
    const ids = this.getSelectedData().map(row => row.id);
    console.log("Deleting rows", ids);
    this.deleteRow(ids);
}

function setupButtonListeners(table) {
    const deleteButton = document.querySelector("#id_delete_selected_btn");
    deleteButton.addEventListener("click", deleteSelected.bind(table));
}

const table = new Tabulator(
    "#id_entry_table",
    {
        layout: "fitColumns",
        responsiveLayout: "hide",
        selectable: true,
        columns: [
            {
                responsive: 35,
                width: 50,
                formatter: "rowSelection",
                titleFormatter: "rowSelection",
                titleFormatterParams: {
                    rowRange: "active",
                },
                hozAlign: "center",
                headerHozAlign: "center",
                headerSort: false,
            },
            {
                title: "Date",
                responsive: 10,
                width: 220,
                frozen: true,
                formatter: "datetime",
                formatterParams:{
                    inputFormat:"yyyy-MM-dd",
                    outputFormat:"DD",
                },
                headerFilter: rangeEditor,
                headerFilterFunc: rangeFilter,
                headerFilterLiveFilter: false,
                editor: "date",
                validator: "required",
            },
            {
                title: "Amount",
                minWidth: 97,
                widthGrow: 1,
                responsive: 10,
                sorter: "number",
                editor: "number",
                editorParams: {
                    selectContents: true,
                    min: 0,
                },
                headerFilter: comparisonEditor,
                headerFilterFunc: comparisonFilter,
                headerFilterLiveFilter: true,
                validator: "required",
            },
            {
                title: "Category",
                minWidth: 70,
                widthGrow: 2,
                responsive: 20,
                headerFilter: "input",
                headerFilterPlaceholder: "Filter category",
                editor: "input",
                editorParams: {
                    selectContents: true,
                },
                validator: "required",
            },
            {
                title: "Tags",
                minWidth: 70,
                widthGrow: 3,
                responsive: 30,
                headerFilter: "input",
                headerFilterPlaceholder: "Filter tags",
                editor: "input",
                editorParams: {
                    selectContents: true,
                },
            },
            {
                title: "Comment",
                minWidth: 70,
                widthGrow: 5,
                responsive: 40,
                headerFilter: "input",
                headerFilterPlaceholder: "Filter comment",
                editor: "textarea",
                editorParams: {
                    selectContents: true,
                    shiftEnterSubmit: true,
                },
            },
            {
                title: "Edit",
                responsive: 50,
                width: 45,
                formatter: "html",
            },
            {
                title: "Delete",
                width: 65,
                responsive: 50,
                formatter: "html",
            },
        ],
    },
);

// Make the table visible once it's built
table.on(
    "tableBuilt",
    () => {
        document.querySelector("#id_entry_table").style.visibility = "visible";
    },
);

setupButtonListeners(table);

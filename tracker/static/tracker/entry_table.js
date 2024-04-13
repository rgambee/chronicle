// Class for a single entry
// Must match the server-side equivalent: tracker.models.Entry
class Entry {
    id;
    amount;
    date;
    category;
    tags;
    comment;

    constructor(id, amount, date, category, tags, comment) {
        this.id = Number.parseInt(id);
        this.amount = Number.parseFloat(amount);
        this.date = date;
        this.category = category;
        this.tags = tags.split(", ")
            .map((tag) => tag.trim())
            .filter((tag) => tag.length > 0);
        this.comment = comment;
    }

    static fromRow(rowComponent) {
        const rowData = rowComponent.getData();
        return new Entry(
            rowData.id,
            rowData.amount,
            rowData.date,
            rowData.category,
            rowData.tags,
            rowData.comment,
        );
    }
}

// Class to encapsulate user modifications to send back to the server
class UserUpdates {
    deletions;
    edits;

    constructor(deletions, edits) {
        this.deletions = Array.from(deletions).map(Number.parseInt).filter(
            n => !Number.isNaN(n),
        );
        this.edits = edits;
    }

    static fromTable(table) {
        // Use Set to deduplicate rows
        const editedRowIds = new Set(table.getEditedCells().map(
            cell => cell.getRow().getIndex(),
        ));
        const entries = [];
        editedRowIds.forEach(
            id => {
                if (table.deletedRowIds === undefined || !table.deletedRowIds.has(id)) {
                    entries.push(Entry.fromRow(table.getRow(id)));
                }
            },
        );
        return new UserUpdates(
            table.deletedRowIds || [],
            entries,
        );
    }
}


// Custom date filtering based on this answer by Oli Folkerd:
// https://stackoverflow.com/a/64414478
function dateRangeEditor(cell, onRendered, success, cancel) {
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

function dateRangeFilter(dateRange, dateValue) {
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

function amountRangeEditor(cell, onRendered, success) {
    const template = document.querySelector("#id_amount_range_template");
    const comparison = template.content.cloneNode(true);
    const amountInputMin = comparison.querySelector("#id_amount_range_min");
    const amountInputMax = comparison.querySelector("#id_amount_range_max");

    function buildRange() {
        let amountMin = parseFloat(amountInputMin.value);
        if (Number.isNaN(amountMin)) {
            amountMin = 0;
        }
        let amountMax = parseFloat(amountInputMax.value);
        if (Number.isNaN(amountMax)) {
            amountMax = Number.POSITIVE_INFINITY;
        }

        success(
            {
                min: amountMin,
                max: amountMax,
            },
        );
    }

    amountInputMin.addEventListener("input", buildRange);
    amountInputMax.addEventListener("input", buildRange);

    return comparison.firstElementChild;
}

function amountRangeFilter(amountRange, amountValue) {
    return amountRange.min <= amountValue && amountValue <= amountRange.max;
}

// Function must be bound to an instance of Tabulator
function deleteSelected() {
    const ids = this.getSelectedData().map(row => row.id);
    console.log("Deleting rows", ids);
    this.deleteRow(ids);
    // Store deleted rows so they can be sent to server when the user saves changes
    if (this.deletedRowIds === undefined) {
        this.deletedRowIds = new Set();
    }
    ids.forEach(id => this.deletedRowIds.add(id));
}

function undoListener(action, component, data) {
    console.log("undo", action, component, data);
    if (action !== "rowDelete") {
        return;
    }
    const table = component.getTable();
    if (table.deletedRowIds !== undefined) {
        table.deletedRowIds.delete(component.getIndex());
    }
}

function redoListener(action, component, data) {
    console.log("redo", action, component, data);
    const table = component.getTable();
    if (table.deletedRowIds !== undefined) {
        table.deletedRowIds.add(component.getIndex());
    }
}

// Function must be bound to an instance of Tabulator
function saveChanges() {
    console.log("Deleted rows", this.deletedRowIds);
    console.log("Edited cells", this.getEditedCells());

    // TODO: validate edited cells
    const form = document.querySelector("#id_entry_updates_form");
    const data = new FormData(form);
    const updates = UserUpdates.fromTable(this);
    data.append("updates", JSON.stringify(updates));
    console.log(JSON.stringify(updates));

    function onResponse(response) {
        if (!response.ok) {
            // TODO: notify user
            console.error("Received error in response to entry updates");
            console.info(response);
            return;
        }
        console.info("Updates successful");
        // Clear pending edits now that they've been saved
        if (this.deletedRowIds !== undefined) {
            this.deletedRowIds.clear();
        }
        this.clearCellEdited();
        // Don't let undo history span saves. It would be possible to let the user undo
        // a change even after it's been sent to the server. But that's not worth the
        // added complexity at this stage. Such a feature could be implemented in the
        // future if desired.
        this.clearHistory();
    }

    fetch(
        form.action,
        {
            method: form.method,
            body: data,
        },
    ).then(onResponse.bind(this)).catch(console.error);
}

function setupButtonListeners(table) {
    const deleteButton = document.querySelector("#id_delete_selected_btn");
    deleteButton.addEventListener("click", deleteSelected.bind(table));

    const undoButton = document.querySelector("#id_undo_btn");
    undoButton.addEventListener("click", () => table.undo());
    table.on("historyUndo", undoListener);

    const redoButton = document.querySelector("#id_redo_btn");
    redoButton.addEventListener("click", () => table.redo());
    table.on("historyRedo", redoListener);

    const saveButton = document.querySelector("#id_save_changes_btn");
    saveButton.addEventListener("click", saveChanges.bind(table));
}

function createTable() {
    const table = new Tabulator(
        "#id_entry_table",
        {
            layout: "fitColumns",
            responsiveLayout: "hide",
            selectable: true,
            history: true,
            index: "id",
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
                    title: "Id",
                    visible: false,
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
                    headerFilter: dateRangeEditor,
                    headerFilterFunc: dateRangeFilter,
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
                    formatter: "money",
                    formatterParams: {
                        precision: false,
                    },
                    headerFilter: amountRangeEditor,
                    headerFilterFunc: amountRangeFilter,
                    headerFilterLiveFilter: false,
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
            ],
        },
    );
    // Make the table visible once it's built (it's hidden initially by the HTML)
    table.on(
        "tableBuilt",
        () => {
            document.querySelector("#id_entry_table").style.visibility = "visible";
        },
    );
    return table;
}

const table = createTable();
setupButtonListeners(table);

new Tabulator(
    "#entry-table",
    {
        responsiveLayout: "hide",
        columns: [
            {
                title: "Date",
                responsive: 10,
            },
            {
                title: "Amount",
                sorter: "number",
                responsive: 10,
            },
            {
                title: "Category",
                responsive: 20,
            },
            {
                title: "Tags",
                responsive: 30,
            },
            {
                title: "Comment",
                responsive: 40,
            },
            {
                title: "Edit",
                responsive: 50,
            },
            {
                title: "Delete",
                responsive: 50,
            },
        ],
    },
);

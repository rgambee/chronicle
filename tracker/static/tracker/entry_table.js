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
            },
            {
                title: "Amount",
                sorter: "number",
                responsive: 10,
            },
            {
                title: "Category",
                responsive: 20,
                formatter: "html",
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

var table = new Tabulator("#dl-txs-table", {
    // data: [],           //load row data from array
    ajaxURL: txsApiUrl,
    ajaxResponse: function (url, params, response) {

        return response.data.map(
            (r) => {
                // let debit_amt = null;
                // let credit_amt = null;
                if (r.tx_type === "credit") {
                    r.credit_amt = r.amount;
                    r.debit_amt = null;
                } else if (r.tx_type === "debit") {
                    r.debit_amt = r.amount;
                    r.credit_amt = null;
                }
                return r
            }
        );
    },
    layout: "fitColumns",      //fit columns to width of table
    responsiveLayout: "hide",  //hide columns that dont fit on the table
    tooltips: true,            //show tool tips on cells
    addRowPos: "top",          //when adding a new row, add it to the top of the table
    history: true,             //allow undo and redo actions on the table
    pagination: "local",       //paginate the data
    paginationSize: 7,         //allow 7 rows per page of data
    movableColumns: true,      //allow column order to be changed
    resizableRows: true,       //allow row order to be changed
    initialSort: [             //set the initial sort order of the data
        {column: "account_id", dir: "asc"},
    ],
    columns: [                 //define the table columns

        // {title: "Name", field: "name", editor: "input"},
        // {title: "Task Progress", field: "progress", align: "left", formatter: "progress", editor: true},
        // {title: "Gender", field: "gender", width: 95, editor: "select", editorParams: {values: ["male", "female"]}},
        // {title: "Rating", field: "rating", formatter: "star", align: "center", width: 100, editor: true},
        // {title: "Color", field: "col", width: 130, editor: "input"},
        // {title: "Date Of Birth", field: "dob", width: 130, sorter: "date", align: "center"},
        // {
        //     title: "Driver",
        //     field: "car",
        //     width: 90,
        //     align: "center",
        //     formatter: "tickCross",
        //     sorter: "boolean",
        //     editor: true
        // },

        {title: "Account Code", field: "account__code"},
        {title: "Account Name", field: "account__name"},
        {title: "Credit", field: "credit_amt", align: "right"},
        {title: "Debit", field: "debit_amt", align: "right"},
        {title: "Description", field: "description"},

    ],
    paginationSize: 20
});

table.setData();
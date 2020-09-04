import Chart, {ChartOptions, ChartTitleOptions, ChartTooltipOptions} from "chart.js";
import Axios, {AxiosInstance, AxiosResponse} from "axios";

function currencyFormatter(value: number): string {
    return Intl.NumberFormat(
        'en-US',
        {style: 'currency', currency: 'USD'})
        .format(value);
}


interface DjangoLedgerJSONDataResponse {
    results: object
}

class BaseChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;
    baseURL: string;

    constructor(selector: string, entitySlug: string, chartData = null) {
        this.baseURL = 'http://127.0.0.1:8000/';
        this.entitySlug = entitySlug;
        this.endPoint = this.getEndPoint();
        this.selector = selector;
        if (!chartData) {
            this.startHttpClient()
        }
    }

    getBaseURL(): string {
        return this.baseURL;
    }

    // @ts-ignore
    getEndPoint(): string {
    }

    getChartData() {
        if (!this.chartData) {
            this.http?.get(
                this.endPoint
            ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse>) => {
                this.chartData = r.data;
                if (this.consoleLogData) {
                    console.log(r);
                }
                this.renderChart()
            })
        } else {
            this.renderChart()
        }
    }

    startHttpClient() {
        this.http = Axios.create({
            baseURL: this.getBaseURL()
        })
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    renderChart() {


    }

}

class PnLChart extends BaseChart {


    getEndPoint() {
        return `entity/${this.entitySlug}/data/pnl/`
    }


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let entityName = this.chartData.results['entity_name']
            // @ts-ignore
            let pnlData = this.chartData.results['pnl_data']
            let chartLabels = Object.keys(pnlData);
            let revenue = chartLabels.map(k => {
                // @ts-ignore
                return pnlData[k]['GROUP_INCOME']
            })
            let netIncome = chartLabels.map(k => {
                // @ts-ignore
                return pnlData[k]['GROUP_EARNINGS']
            })

            let data = {
                labels: chartLabels,
                datasets: [
                    {
                        label: 'Income',
                        backgroundColor: 'rgb(255,127,153)',
                        borderColor: 'rgb(255, 99, 132)',
                        data: revenue
                    },
                    {
                        label: 'Earnings',
                        backgroundColor: 'rgb(110,210,81)',
                        borderColor: 'rgb(115,255,99)',
                        data: netIncome
                    }]
            }

            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return currencyFormatter(value);

                    }
                }
            }


            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: `${entityName} - Income & Earnings`,
                fontSize: 20
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions,
                tooltips: tooltipOptions,
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true
                            }
                        }
                    ]
                }
            }

            this.chart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: chartOptions
            });
        }

    }

}

class NetPayablesChart extends BaseChart {


    getEndPoint() {
        return `entity/${this.entitySlug}/data/net-payables/`
    }


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let netPayablesData = this.chartData.results['net_payable_data']
            let chartLabels = Object.keys(netPayablesData);
            let netPayablesDataSet = chartLabels.map(k => {
                // @ts-ignore
                return netPayablesData[k]
            });
            let chartLabelsFormatted = chartLabels.map(k => {
                // @ts-ignore
                return k.replace("_", " ").toUpperCase()
            });
            let data = {
                labels: chartLabelsFormatted,
                datasets: [
                    {
                        // label: 'Income',
                        borderColor: 'rgb(195,195,195)',
                        borderWidth: 0.75,
                        backgroundColor: [
                            'rgba(102, 24, 0, 1)',
                            'rgba(255, 95, 46, 1)',
                            'rgba(252, 190, 50, 1)',
                            'rgba(0,210,1,1)',
                            'rgba(225, 238, 246, 1)',
                        ],
                        data: netPayablesDataSet
                    }
                ]
            }


            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: "Net Payables 0-90+ Days",
                fontSize: 20
            }
            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return currencyFormatter(value);

                    }
                }
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions,
                tooltips: tooltipOptions
            }

            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: chartOptions
            });
        }

    }

}

class NetReceivablesChart extends BaseChart {


    getEndPoint() {
        return `entity/${this.entitySlug}/data/net-receivables/`
    }


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let netPayablesData = this.chartData.results['net_payable_data']
            let chartLabels = Object.keys(netPayablesData);
            let netPayablesDataSet = chartLabels.map(k => {
                // @ts-ignore
                return netPayablesData[k]
            });
            let chartLabelsFormatted = chartLabels.map(k => {
                // @ts-ignore
                return k.replace("_", " ").toUpperCase()
            });
            let data = {
                labels: chartLabelsFormatted,
                datasets: [
                    {
                        // label: 'Income',
                        borderColor: 'rgb(195,195,195)',
                        borderWidth: 0.75,
                        backgroundColor: [
                            'rgba(102, 24, 0, 1)',
                            'rgba(255, 95, 46, 1)',
                            'rgba(252, 190, 50, 1)',
                            'rgba(0,210,1,1)',
                            'rgba(225, 238, 246, 1)',
                        ],
                        data: netPayablesDataSet
                    }
                ]
            }


            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: "Net Receivables 0-90+ Days",
                fontSize: 20
            }
            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return currencyFormatter(value);

                    }
                }
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions,
                tooltips: tooltipOptions
            }

            this.chart = new Chart(ctx, {
                type: 'pie',
                data: data,
                options: chartOptions
            });
        }

    }

}

export {PnLChart, NetPayablesChart, NetReceivablesChart};


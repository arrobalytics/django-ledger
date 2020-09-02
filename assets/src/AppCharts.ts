import Chart, {ChartOptions, ChartTitleOptions} from "chart.js";
import Axios, {AxiosInstance, AxiosResponse} from "axios";


interface EntityPnLDataResponse {
    entity_slug: string,
    entity_name: string,
    pnl_data: object
}

interface DjangoLedgerJSONDataResponse {
    results: EntityPnLDataResponse
}


class PnLChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;


    constructor(selector: string, entitySlug: string) {
        this.entitySlug = entitySlug;
        this.endPoint = this.getEndPoint();
        this.selector = selector;
        this.getHttpClient()
    }

    getEndPoint() {
        return `entity/${this.entitySlug}/data/pnl/`
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse>) => {
            this.chartData = r.data;
            if (this.consoleLogData) {
                console.log(r);
            }
            this.renderChart()
        })
    }


    renderChart() {

        if (this.chartData) {
            let entityName = this.chartData.results.entity_name
            let pnlData = this.chartData.results.pnl_data
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

            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: `${entityName} - Income & Earnings`,
                fontSize: 20
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions
            }

            this.chart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: chartOptions
            });
        }

    }

}

interface EntityPnLDataResponse2 {
    entity_slug: string,
    net_payable_data: object
}

interface DjangoLedgerJSONDataResponse2 {
    results: EntityPnLDataResponse2
}


class NetPayablesChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse2 | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;


    constructor(selector: string, entitySlug: string) {
        this.entitySlug = entitySlug;
        this.endPoint = this.getEndPoint();
        this.selector = selector;
        this.getHttpClient()
    }

    getEndPoint() {
        return `entity/${this.entitySlug}/data/net-payables/`
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse2>) => {
            this.chartData = r.data;
            if (this.consoleLogData) {
                console.log(r);
            }
            this.renderChart()
        })
    }


    renderChart() {

        if (this.chartData) {
            // let entityName = this.chartData.results.entity_name
            let netPayablesData = this.chartData.results.net_payable_data
            let chartLabels = Object.keys(netPayablesData);
            let netPayablesDataSet = chartLabels.map(k => {
                // @ts-ignore
                return netPayablesData[k]
            });
            let data = {
                labels: chartLabels,
                datasets: [
                    {
                        // label: 'Income',
                        backgroundColor: [
                            'rgba(255, 54, 45, 1)',
                            'rgba(137, 212, 244, 1)',
                            'rgba(255, 209, 14, 1)',
                            'rgb(237,232,216)',
                            'rgba(1, 73, 5, 1)'],
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

            let chartOptions: ChartOptions = {
                title: chartTitleOptions
            }

            this.chart = new Chart(ctx, {
                type: 'pie',
                data: data,
                options: chartOptions
            });
        }

    }

}

export {PnLChart, NetPayablesChart};


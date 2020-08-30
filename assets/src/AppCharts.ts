import Chart from "chart.js";
import Axios, {AxiosInstance} from "axios";

class RevenueAndNetIncome {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: object | undefined;
    http: AxiosInstance | undefined;


    constructor(selector: string) {
        this.endPoint = '/data';
        this.selector = selector;
        this.getHttpClient()
        this.renderChart()
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        // this.getChartData()
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then(r => {
            this.chartData = r;
            console.log(r);
            this.renderChart()
        })
    }


    renderChart() {

        let data = {
            labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
            datasets: [
                {
                    label: 'Revenue',
                    backgroundColor: 'rgb(255,127,153)',
                    borderColor: 'rgb(255, 99, 132)',
                    data: [5, 10, 5, 2, 20, 30, 45]
                },
                {
                    label: 'Net Income',
                    backgroundColor: 'rgb(110,210,81)',
                    borderColor: 'rgb(115,255,99)',
                    data: [1.2, -2.3, -4, .2, 5.6, 10.2, 19.6]
                }]
        }


        // @ts-ignore
        var ctx = document.getElementById(this.selector).getContext('2d');
        this.chart = new Chart(ctx, {
            // The type of chart we want to create
            type: 'bar',
            data: data,

            // Configuration options go here
            options: {}
        });
    }

}

export {RevenueAndNetIncome};

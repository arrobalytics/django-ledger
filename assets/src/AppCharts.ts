import Chart from "chart.js";
import Axios, {AxiosInstance} from "axios";

class ProfitChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: object | undefined;
    http: AxiosInstance | undefined;


    constructor(selector: string) {
        this.endPoint = '/data';
        this.selector = selector;
        // this.getHttpClient()
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
        // @ts-ignore
        var ctx = document.getElementById(this.selector).getContext('2d');
        this.chart = new Chart(ctx, {
            // The type of chart we want to create
            type: 'line',

            // The data for our dataset
            data: {
                labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
                datasets: [{
                    label: 'My First dataset',
                    backgroundColor: 'rgb(255, 99, 132)',
                    borderColor: 'rgb(255, 99, 132)',
                    data: [0, 10, 5, 2, 20, 30, 45]
                }]
            },

            // Configuration options go here
            options: {}
        });
    }

}

export {ProfitChart};

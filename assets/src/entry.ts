import {DjetlerApp} from "./DjetlerApp";
import {RevenueAndNetIncome} from "./AppCharts";


export function startDJLApp() {
    return new DjetlerApp();
}

export function renderRnNIChart(id: string) {
    return new RevenueAndNetIncome(id);
}
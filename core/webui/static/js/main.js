import App from './components/App.js';

Vue.config.productionTip = false;
Vue.$cookies.config('10y');

new Vue({
	render: h => h(App)
}).$mount(`#app`);

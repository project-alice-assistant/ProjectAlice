import Header from './header.js';
import Nav from './nav.js';
import Body from './body.js';

import vue from './templates/app.vue.js';

export default {
	name      : 'app',
	components: {
		Header,
		Nav,
		Body
	},
	template  : vue
};

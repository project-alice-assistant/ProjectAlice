(function ($) {
	$.fn.connections = function (options) {
		if (options === "update") {
			return processConnections(update, this);
		} else if (options === "remove") {
			return processConnections(destroy, this);
		} else {
			options = $.extend(
				true,
				{
					borderClasses: {},
					class: "connection",
					css: {},
					from: this,
					tag: "connection",
					to: this,
					within: ":root"
				},
				options
			);
			connect(options);
			return this;
		}
	};

	$.event.special.connections = {
		teardown: function () {
			processConnections(destroy, $(this));
		}
	};

	let connect = function (options) {
		let borderClasses = options.borderClasses;
		let tag = options.tag;
		let end1 = $(options.from);
		let end2 = $(options.to);
		let within = $(options.within);
		delete options.borderClasses;
		delete options.tag;
		delete options.from;
		delete options.to;
		delete options.within;
		within.each(function () {
			let container = this;
			let done = [];
			end1.each(function () {
				let node = this;
				done.push(this);
				end2.not(done).each(function () {
					createConnection(
						container,
						[node, this],
						tag,
						borderClasses,
						options
					);
				});
			});
		});
	};

	let createConnection = function (
		container,
		nodes,
		tag,
		borderClasses,
		options
	) {
		let css = $.extend({position: "absolute"}, options.css);
		let connection = $("<" + tag + "/>", options).css(css);
		connection.appendTo(container);

		let border_w = (connection.outerWidth() - connection.innerWidth()) / 2;
		let border_h = (connection.outerHeight() - connection.innerHeight()) / 2;

		if (border_w <= 0 && border_h <= 0) {
			border_w = border_h = 1;
		}

		let data = {
			borderClasses: borderClasses,
			border_h: border_h,
			border_w: border_w,
			node_from: $(nodes[0]),
			node_to: $(nodes[1]),
			nodes_dom: nodes,
			css: css
		};

		if ("none" === connection.css("border-top-style")) {
			data.css.borderStyle = "solid";
		}
		$.data(connection.get(0), "connection", data);
		$.data(connection.get(0), "connections", [connection.get(0)]);
		for (let i = 0; i < 2; i++) {
			let connections = connection.add($.data(nodes[i], "connections")).get();
			$.data(nodes[i], "connections", connections);
			if (connections.length == 1) {
				$(nodes[i]).on("connections.connections", false);
			}
		}
		update(connection.get(0));
	};

	let destroy = function (connection) {
		let nodes = $.data(connection, "connection").nodes_dom;
		for (let i = 0; i < 2; i++) {
			let connections = $($.data(nodes[i], "connections"))
				.not(connection)
				.get();
			$.data(nodes[i], "connections", connections);
		}
		$(connection).remove();
	};

	let getState = function (data) {
		data.rect_from = data.nodes_dom[0].getBoundingClientRect();
		data.rect_to = data.nodes_dom[1].getBoundingClientRect();
		let cached = data.cache;
		data.cache = [
			data.rect_from.top,
			data.rect_from.right,
			data.rect_from.bottom,
			data.rect_from.left,
			data.rect_to.top,
			data.rect_to.right,
			data.rect_to.bottom,
			data.rect_to.left
		];
		data.hidden =
			0 === (data.cache[0] | data.cache[1] | data.cache[2] | data.cache[3]) ||
			0 === (data.cache[4] | data.cache[5] | data.cache[6] | data.cache[7]);
		data.unmodified = true;
		if (cached === undefined) {
			return (data.unmodified = false);
		}
		for (let i = 0; i < 8; i++) {
			if (cached[i] !== data.cache[i]) {
				return (data.unmodified = false);
			}
		}
	};

	let update = function (connection) {
		let data = $.data(connection, "connection");
		getState(data);
		if (data.unmodified) {
			return;
		}
		let border_h = data.border_h;
		let border_w = data.border_w;
		let from = data.rect_from;
		let to = data.rect_to;
		let b = (from.bottom + from.top) / 2;
		let r = (to.left + to.right) / 2;
		let t = (to.bottom + to.top) / 2;
		let l = (from.left + from.right) / 2;

		let h = ["right", "left"];
		if (l > r) {
			h = ["left", "right"];
			let x = Math.max(r - border_w / 2, Math.min(from.right, to.right));
			r = l + border_w / 2;
			l = x;
		} else {
			l -= border_w / 2;
			r = Math.min(r + border_w / 2, Math.max(from.left, to.left));
		}
		let v = ["bottom", "top"];
		if (t > b) {
			v = ["top", "bottom"];
			let x = Math.max(b - border_h / 2, Math.min(from.bottom, to.bottom));
			b = t + border_h / 2;
			t = x;
		} else {
			b = Math.min(b, Math.max(from.top, to.top));
			t -= border_h / 2;
		}
		let width = r - l;
		let height = b - t;
		if (width < border_w) {
			t = Math.max(t, Math.min(from.bottom, to.bottom));
			b = Math.min(b, Math.max(from.top, to.top));
			l = Math.max(from.left, to.left);
			r = Math.min(from.right, to.right);
			r = l = (l + r - border_w) / 2;
		}
		if (height < border_h) {
			l = Math.max(l, Math.min(from.right, to.right));
			r = Math.min(r, Math.max(from.left, to.left));
			t = Math.max(from.top, to.top);
			b = Math.min(from.bottom, to.bottom);
			b = t = (t + b - border_h) / 2;
		}
		width = r - l;
		height = b - t;
		width <= 0 && (border_h = 0);
		height <= 0 && (border_w = 0);
		let style =
			"border-" +
			v[0] +
			"-" +
			h[0] +
			"-radius: 0;" +
			"border-" +
			v[0] +
			"-" +
			h[1] +
			"-radius: 0;" +
			"border-" +
			v[1] +
			"-" +
			h[0] +
			"-radius: 0;";
		(border_h <= 0 || border_w <= 0) &&
		(style += "border-" + v[1] + "-" + h[1] + "-radius: 0;");
		if (data.hidden) {
			style += "display: none;";
		} else {
			data.css["border-" + v[0] + "-width"] = 0;
			data.css["border-" + h[0] + "-width"] = 0;
			data.css["border-" + v[1] + "-width"] = border_h;
			data.css["border-" + h[1] + "-width"] = border_w;
			let current_rect = connection.getBoundingClientRect();
			data.css.left = connection.offsetLeft + l - current_rect.left;
			data.css.top = connection.offsetTop + t - current_rect.top;
			data.css.width = width - border_w;
			data.css.height = height - border_h;
		}
		let bc = data.borderClasses;
		$(connection)
			.removeClass(bc[v[0]])
			.removeClass(bc[h[0]])
			.addClass(bc[v[1]])
			.addClass(bc[h[1]])
			.attr("style", style)
			.css(data.css);
	};

	let processConnections = function (method, elements) {
		return elements.each(function () {
			let connections = $.data(this, "connections");
			if (connections instanceof Array) {
				for (let i = 0, len = connections.length; i < len; i++) {
					method(connections[i]);
				}
			}
		});
	};
})(jQuery);

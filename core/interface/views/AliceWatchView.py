from flask import jsonify, render_template, request

from core.interface.model.View import View


class AliceWatchView(View):
	route_base = '/alicewatch/'


	def index(self):
		super().index()
		return render_template(template_name_or_list='alicewatch.html',
		                       **self._everyPagesRenderValues)


	def verbosity(self):
		try:
			self.AliceWatchManager.verbosity = int(request.form.get('verbosity'))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Error setting verbosity: {e}')
			return jsonify(success=False)

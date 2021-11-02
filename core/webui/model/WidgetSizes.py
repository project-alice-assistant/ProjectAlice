#  Copyright (c) 2021
#
#  This file, WidgetSizes.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:49 CEST

from enum import Enum


class WidgetSizes(Enum):
	w_tiny = '50x50'
	w_tiny_wide = '100x50'
	w_tiny_tall = '50x100'
	w_small = '100x100'
	w_small_wide = '200x100'
	w_small_tall = '100x200'
	w = '200x200'
	w_wide = '300x200'
	w_tall = '200x300'
	w_large = '300x300'
	w_large_wide = '400x300'
	w_large_tall = '300x400'
	w_extralarge = '500x500'
	w_extralarge_wide = '700x500'
	w_extralarge_tall = '500x700'

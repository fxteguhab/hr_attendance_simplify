{
	'name': 'HR Attendance Simplify',
	'version': '0.1',
	'category': 'Human Resources',
	'description': """
		Simplify attendance entries such that there is only one pair (sign in and sign out) of employee 
		attendance entries per day. This is needed in case employees can log their attendance 
		more than twice everyday.
	""",
	'author': 'Christyan Juniady and Associates',
	'maintainer': 'Christyan Juniady and Associates',
	'website': 'http://www.chjs.biz',
	'depends': ["base", "web", "hr","hr_attendance"],
	'sequence': 150,
	'data': [
		'cron/hr_attendance_simplify.xml'
	],
	'demo': [
	],
	'test': [
	],
	'installable': True,
	'auto_install': False,
	'qweb': [
	]
}

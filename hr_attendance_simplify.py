from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
from openerp import SUPERUSER_ID

class hr_attendance(osv.osv):

	_inherit = 'hr.attendance'

	_columns = {
		'simplify_state': fields.selection((
			('unprocessed', 'Unprocessed'),
			('simplified', 'Simplified'),
			('removed', 'Removed'),
			), 'Simplification Process State'),
		'active': fields.boolean('Displayed'),
	}

	_defaults = {
		'simplify_state': 'unprocessed',
		'active': True,
	}

	_backdate = 1 # mau ngambil berapa hari ke belakang sebelum diproses. 1 artinya ambil yang kemaren ke belakang.

	def _altern_si_so(self, cr, uid, ids, context=None):
	# dioverride supaya memberikan kebabasan kepada klien untuk (sebelum di-simplify) me-log 
	# attendance tanpa harus selang-seling sign in - sign out.
		return True

	_constraints = [(_altern_si_so, _('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)'), ['action'])]

	def simplify_per_employee(self, cr, uid, attendance_data, tz, context={}):
	# behaviour standard:
	# - kalau hanya satu baris dibiarkan saja (tidak ada simplifikasi)
	# - kalau 2 baris atau lebih maka dikenakan aturan yang paling pagi adalah sign in 
	#   dan yang paling sore adalah sign out. semua entri di tengah2nya adalah action 
	#   (alias di-hide dari tampilan)
		for attn_date in attendance_data:
			attendance_data[attn_date] = sorted(attendance_data[attn_date], key=lambda k: k['name'])
			earliest = 0
			latest = len(attendance_data[attn_date]) - 1
		# kalau ngga ada ya udah
			if latest < 0: continue
		# kalau hanya satu entri, asumsikan pasti sign in
			if latest == 0: 
				self.write(cr, uid, [attendance_data[attn_date][0].id], {
					'action': 'sign_in', 
					'simplify_state': 'simplified'
				})
				continue 
		# kalau lebih dari satu entri barulah diproses 
		# selain yang pertama dan terakhir, nonaktifkan supaya hidden/unsearchable
			for idx, entry in enumerate(attendance_data[attn_date]):
				if idx == earliest or idx == latest: # skip yang pertama dan terakhir
				# ini dibutuhkan supaya constraint alternate sign in/sign out tidak terlanggar
					self.write(cr, uid, [entry.id], {'action': 'action'})
				else:
					self.write(cr, uid, [entry.id], {
						'simplify_state': 'removed',
						'active': False,
						'action': 'action',
						})
		# entry pertama adalah sign in, entry terakhir sign out
			self.write(cr, uid, [attendance_data[attn_date][earliest].id], {
				'simplify_state': 'simplified',
				'action': 'sign_in',
				})
			self.write(cr, uid, [attendance_data[attn_date][latest].id], {
				'simplify_state': 'simplified',
				'action': 'sign_out',
				})

	def cron_simplify_attendance(self, cr, uid, context={}):
	# ambil user timezone. user yang dipakai adalah SUPERUSER, so pastikan timezone superuser
	# idem timezone server
		user_obj = self.pool.get('res.users')
		user = user_obj.browse(cr, SUPERUSER_ID, SUPERUSER_ID)
		if not user.partner_id.tz:
			raise osv.except_osv(_('Attendance Error'),_('Please set SUPERUSER timezone first.'))
		tz = pytz.timezone(user.partner_id.tz) or pytz.utc
	# ambil semua yang belum diproses simplify
	# jangan yang hari ini, soalnya diasumsikan pegawainya masih bisa absen lagi sepanjang hari
		today = datetime.now(tz).replace(hour=23, minute=59, second=59)
		backdate = today - timedelta(hours=24*self._backdate)
		attendance_ids = self.search(cr, uid, [
			('simplify_state','=','unprocessed'),
			('name','<=',backdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
			], order='employee_id, name')
	# proses sedemikian sehingga attendances berisi data dikelompokkan per pegawai per hari
		attendances = {}
		for data in self.browse(cr, uid, attendance_ids):
			key = data.employee_id.id
			key2 = datetime.strptime(data.name, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
			if key not in attendances: attendances.update({key: {}})
			if key2 not in attendances[key]: attendances[key].update({key2: []})
			attendances[key][key2].append(data)
	# di titik ini sudah dipisahkan per employee per hari
	# untuk setiap kelompok data, proses sehingga per employee perhari tinggal dua entri
	# sengaja pakai method terpisah supaya bisa dioverride
		for employee_id in attendances:
			self.simplify_per_employee(cr, uid, attendances[employee_id], tz, context=context)


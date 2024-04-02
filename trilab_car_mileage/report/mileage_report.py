from odoo import fields, models, api


class MileageReport(models.TransientModel):
    """
    The Mileage Report model facilitates the generation of detailed reports for vehicles.
    """

    _name = 'mileage.report.model'
    _description = 'Mileage Report'

    name = fields.Char(string='Mileage Report', default='Mileage Report')
    start_date = fields.Date(string='Start Date', required=True, help='Defines the beginning of the reporting period.')
    end_date = fields.Date(string='End Date', required=True, help='Defines the end of the reporting period.')
    odometer_at_start = fields.Integer(
        string='Odometer At Start',
        compute='_compute_odometer_at_start',
        help='Automatically calculated odometer reading at the start of the first trip within the report’s time frame.',
    )
    odometer_at_end = fields.Integer(
        string='Odometer At End',
        compute='_compute_odometer_at_end',
        help='Automatically calculated odometer reading at the end of the last trip within the report’s time frame.',
    )
    total_distance = fields.Integer(
        string='Total Distance',
        compute='_compute_total_distance',
        help='The total distance traveled by the vehicle within the specified period.',
    )
    registration_id = fields.Many2one(
        'vehicle.model',
        string='Registration Number',
        help='Selects the vehicle for which the report is being generated.',
    )
    driver_id = fields.Many2one(
        'res.users', help='Displays the primary driver associated with the vehicle for the specified period.'
    )
    mileage_ids = fields.One2many(
        'mileage.model',
        compute='_compute_mileages_ids',
        help='Lists all mileage records associated with the vehicle that fall within the specified date range.',
    )

    @api.onchange('start_date', 'end_date', 'registration_id', 'driver_id')
    def _compute_mileages_ids(self):
        """
        Compiles a list of mileage records associated with the selected vehicle that fall within the defined date range.
        """
        self.mileage_ids = self.env['mileage.model'].search(
            [
                ('departure_date', '>=', self.start_date),
                ('return_date', '<=', self.end_date),
                ('vehicle_id', '=', self.registration_id.id),
                ('driver_id', '=', self.driver_id.id),
            ],
            order="departure_date desc, odometer_at_end desc",
        )

    @api.onchange('start_date', 'end_date', 'registration_id', 'driver_id')
    def _compute_odometer_at_start(self):
        """
        Calculates the odometer reading at the beginning of the earliest trip within the reporting period.
        """
        if self.mileage_ids:
            self.odometer_at_start = (
                previous_odometer_reading
                if (previous_odometer_reading := self.mileage_ids[-1].get_previous_odometer())
                else 0
            )

    @api.onchange('start_date', 'end_date', 'registration_id', 'driver_id')
    def _compute_odometer_at_end(self):
        """
        Determines the odometer reading at the end of the latest trip within the reporting period.
        """
        self.odometer_at_end = (
            max(odometers_list) if (odometers_list := self.mileage_ids.mapped('odometer_at_end')) else 0
        )

    @api.onchange('start_date', 'end_date', 'registration_id', 'driver_id')
    def _compute_total_distance(self):
        self.total_distance = sum(self.mileage_ids.mapped('traveled_distance'))

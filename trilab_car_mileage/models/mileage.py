from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Mileage(models.Model):
    """
    This model tracks details about vehicle trips.
    """

    _name = "mileage.model"
    _description = "Mileage Model"
    _order = "departure_date desc, odometer_at_end desc"

    name = fields.Char(default='Mileage Record')
    departure_date = fields.Date(
        string="Date Of Departure",
        required=True,
        default=fields.Date.today,
        index=True,
        help="Date when the trip started.",
    )
    return_date = fields.Date(
        string="Date Of Return", required=True, default=fields.Date.today, index=True, help="Date when the trip ended."
    )
    trip_reason = fields.Char(string="Trip Reason", required=True, help="Purpose of the trip.")
    start_location = fields.Char(string="Start Location", required=True, help="Starting location of the trip.")

    end_location = fields.Char(string="End Location", required=True, help="Final destination of the trip.")
    odometer_at_end = fields.Integer(
        string="Odometer Reading at end",
        required=True,
        index=True,
        help="Vehicle's odometer reading at the end of the trip.",
        group_operator=False,
    )
    traveled_distance = fields.Integer(
        string="Traveled Distance",
        compute="_compute_traveled_distance",
        default=0,
        help="Automatically calculated traveled distance.",
    )
    row_number = fields.Integer(
        string='#',
        compute='_compute_row_number',
        help='This field dynamically assigns a row number to each record')
    vehicle_id = fields.Many2one(
        "vehicle.model",
        string="Registration Number",
        ondelete="cascade",
        readonly=True,
        help="Vehicle used for the trip.",
    )
    driver_id = fields.Many2one(
        "res.users",
        string="Driver",
        default=lambda self: self.env.user,
        ondelete="cascade",
        readonly=True,
        help="Driver of the vehicle.",
    )

    @api.depends('traveled_distance')  # Zmieniłem trigger, bo row_number nie zależy bezpośrednio od traveled_distance
    def _compute_row_number(self):
        """
        Calculates and assigns a row number for each record individually.
        """
        for index, rec in enumerate(self, start=1):
            rec.row_number = index

    def get_previous_odometer(self):
        """
        Fetches the previous odometer reading for the same vehicle, prioritizing records by date
        and odometer reading.
        """
        if previous_odometer := self.sudo().search_fetch(
            [
                "|",
                "&",
                ("odometer_at_end", "<", self.odometer_at_end),
                ("departure_date", "=", self.departure_date),
                "&",
                ("departure_date", "<", self.departure_date),
                ("vehicle_id", "=", self.vehicle_id.id),
            ],
            ["odometer_at_end"],
            limit=1,
        ):
            return previous_odometer[0].odometer_at_end
        return None

    @api.depends("odometer_at_end")
    def _compute_traveled_distance(self):
        """
        Computes the distance traveled by subtracting the current odometer reading from the
        previous odometer reading.
        """
        for rec in self:
            rec.traveled_distance = (
                rec.odometer_at_end - previous_odometer
                if (previous_odometer := rec.get_previous_odometer())
                else rec.odometer_at_end
            )

    @api.constrains("departure_date", "return_date")
    def _check_dates(self):
        """
        Validates that the departure date is before or the same as the return date,
        ensures no overlapping dates for the same vehicle and prevent from entering future date.
        """
        if self.sudo().search_count(
            [("id", "!=", self.id), ("vehicle_id", "=", self.vehicle_id.id), ("return_date", ">", self.departure_date)],
            limit=1,
        ):
            raise ValidationError("You cannot input mileage with a date preceding the last entry")

        if self.departure_date > self.return_date:
            raise ValidationError("The departure date cannot be later than the return date.")

        if any(date > fields.Date.today() for date in [self.departure_date, self.return_date]):
            raise ValidationError("You can't input a future date")

    @api.constrains("odometer_at_end")
    def _check_odometer(self):
        """
        Ensures that the odometer reading at the end of a trip is greater than the previous
        odometer reading for the same vehicle, with a minimum traveled distance of 1 km.
        """

        if (previous_odometer := self.get_previous_odometer()) and self.odometer_at_end < previous_odometer:
            raise ValidationError("A record with an earlier date has a higher odometer reading, which is inconsistent.")

        if previous_odometer and (self.odometer_at_end - previous_odometer) < 1:
            raise ValidationError("Mileage distance can't be shorter than 1 km.")

        if self.odometer_at_end < 1:
            raise ValidationError("The odometer reading cannot be negative or 0.")

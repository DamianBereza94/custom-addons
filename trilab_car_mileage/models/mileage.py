from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Mileage(models.Model):
    """
    The Mileage model tracks details about vehicle trips, including departure and return dates,
    odometer readings, and trip reasons. It ensures there are no overlapping dates for the same vehicle
    and validates the correctness of odometer entries.
    """

    _name = "mileage.model"
    _description = "Mileage Record"
    _order = "departure_date desc, odometer_at_end desc"

    departure_date = fields.Date(
        string="Date Of Departure",
        required=True,
        default=fields.Date.today,
        index=True,
        help="Specifies the date when the trip began. This should be the day the vehicle left its initial location.",
    )
    return_date = fields.Date(
        string="Date Of Return",
        required=True,
        default=fields.Date.today,
        index=True,
        help="Indicates the date when the trip ended and the vehicle returned to its final destination.",
    )
    trip_reason = fields.Char("Trip Reason", required=True, help="Describes the purpose of the trip.")

    start_location = fields.Char(string="Start Location", required=True, help="The starting location of the trip.")

    end_location = fields.Char(string="End Location", required=True, help="The final location of the trip")
    odometer_at_end = fields.Integer(
        string="Odometer Reading at End",
        required=True,
        index=True,
        help="The reading of the vehicle's odometer at the end of the trip.",
    )
    traveled_distance = fields.Integer(
        string="Traveled Distance",
        compute="_compute_traveled_distance",
        default=None,
        help="Automatically calculated distance traveled during the trip.",
    )

    vehicle_id = fields.Many2one(
        "vehicle.model",
        string="Registration Number",
        ondelete="cascade",
        readonly=True,
        help="Links this mileage record to a specific vehicle from the Vehicle model,"
        "establishing which vehicle was used for the trip.",
    )
    driver_id = fields.Many2one(
        "res.users",
        string="Driver",
        default=lambda self: self.env.user,
        ondelete="cascade",
        readonly=True,
        help="Identifies the user who drove the vehicle for this specific trip."
        "By default, this is set to the current logged-in user.",
    )

    def get_previous_odometer(self):
        """
        Returns the previous mileage record for the same vehicle.
        This search uses logical operators to find records with an earlier odometer reading on the same departure date
        or any record from a previous date, prioritizing the closest records by date and odometer reading.
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

    @api.onchange("odometer_at_end")
    def _compute_traveled_distance(self):
        for rec in self:
            rec.traveled_distance = rec.odometer_at_end - previous_odometer if (
                previous_odometer := rec.get_previous_odometer()) else rec.odometer_at_end

    @api.constrains("departure_date", "return_date")
    def _check_dates(self):
        """
        Ensures that the selected dates do not overlap with another mileage record for the same vehicle.
        This validation prevents conflicting trip records for a single vehicle.
        Still there can be two or more mileage records in one day.
        """
        # Dates order
        for rec in self.sorted(key=lambda r: r.departure_date):
            if self.sudo().search_count(
                [
                    ("id", "not in", self.ids),
                    ("vehicle_id", "=", rec.vehicle_id.id),
                    ("return_date", ">", rec.departure_date),
                ],
                limit=1,
            ):
                raise ValidationError("You cannot input mileage with a date preceding the last entry")
            # Dates validity
            if rec.departure_date > rec.return_date:
                raise ValidationError("The departure date cannot be later than the return date.")

    @api.constrains("odometer_at_end")
    def _check_odometer(self):
        """
        Checks that the new odometer reading is greater than the previous record for the same vehicle
        and ensures that the traveled distance since the last record is at least 1 km.
        This helps maintain the consistency of odometer readings and the logical sequence of travel records.
        """
        # odometer consistency
        for rec in self.sorted(key=lambda r: r.departure_date):
            if (previous_odometer := rec.get_previous_odometer()) and rec.odometer_at_end < previous_odometer:
                raise ValidationError(
                    "A record with an earlier date has a higher odometer reading, which is inconsistent."
                )
            # trip greater then 1km
            if previous_odometer and (rec.odometer_at_end - previous_odometer) < 1:
                raise ValidationError("Mileage distance can't be shorter than 1 km.")
            # not negative first odometer
            if rec.odometer_at_end < 1:
                raise ValidationError("The odometer reading cannot be negative.")

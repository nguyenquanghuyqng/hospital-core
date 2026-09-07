from app.crud.patient import CRUDPatient, crud_patient
from app.crud.queue_ticket import CRUDQueueTicket, crud_queue_ticket
from app.crud.reception import CRUDReception, crud_reception

__all__ = [
    "CRUDPatient", "crud_patient",
    "CRUDQueueTicket", "crud_queue_ticket",
    "CRUDReception", "crud_reception",
]

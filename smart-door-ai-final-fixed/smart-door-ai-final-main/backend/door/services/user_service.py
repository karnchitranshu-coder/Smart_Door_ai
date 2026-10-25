from ..ai.cache import cache
from ..models import Person
from . import supabase_service


def delete_person(person: Person):
    pid = person.id
    person.delete()      # cascades FaceProfiles
    cache.reload()
    supabase_service.delete_person_remote(pid)

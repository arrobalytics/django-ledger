from django.contrib.auth import get_user_model

from django_ledger.models.accounts import AccountModel
from django_ledger.models.entity import EntityModel

UserModel = get_user_model()


def create_coa_structure(coa_data: dict,
                         admin: UserModel,
                         entity: str or EntityModel):
    """
    :param coa_user: Current User Model.
    :param coa_data: New CoA Data.
    :param coa_name: Name of the new Chart of Accounts Model.
    :param coa_desc: Optional Description of the new Chart of Accounts Model.
    :param coa_slug: Optional explicit slug. If not will be created by Django's slugify function based on CoA name.
    """
    print(coa_data)
    if isinstance(entity, str):
        entity, created = EntityModel.objects.get_or_create(slug=entity,
                                                            admin=admin,
                                                            name=entity.upper())
    coa = entity.coa
    acc_objs = [AccountModel(
        code=a['code'],
        name=a['name'],
        role=a['role'],
        balance_type=a['balance_type'],
        coa=coa,
    ) for a in coa_data]
    parents = set([a.get('parent') for a in coa_data])
    children = {
        p: [c['code']
            for c in coa_data if c['parent'] == p and c['code'] != p] for p in parents
    }
    for acc in acc_objs:
        acc.clean()
        acc.save()

    for acc_p, acc_c in children.items():
        p_obj = AccountModel.objects.get(code=acc_p)
        c_qs = AccountModel.objects.filter(code__in=acc_c)
        p_obj.children.set(c_qs)

    return entity

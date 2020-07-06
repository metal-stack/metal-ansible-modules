from metal_python.models import V1IPResponse, V1NetworkResponse


def ip_response(**kwargs):
    return V1IPResponse(**kwargs)


def network_response(**kwargs):
    return V1NetworkResponse(**kwargs)

Layer diagram — views → services → selectors → models
Rule: no ORM in views ever
Rule: no HTTP context (request/response) in services ever
Rule: selectors return querysets or instances, never dicts
Rule: services return model instances or raise exceptions
Rule: all cross-app calls go service → selector, never model → model
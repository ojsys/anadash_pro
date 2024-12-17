def process_participant_data(participant_data):
    """Process participant data from ODK repeat groups"""
    processed_data = []
    
    for p in participant_data.get('repeatPP', []):
        participant = {
            'first_name': p.get('repeatPP/firstNamePP', '').strip(),
            'surname': p.get('repeatPP/surNamePP', '').strip(),
            'gender': p.get('repeatPP/genderPP', ''),
            'phone_number': p.get('repeatPP/phoneNrPP', None),
            'own_phone': p.get('repeatPP/ownPhonePP', '') == 'yes',
            'crops': p.get('repeatPP/cropsPP', ''),
        }
        processed_data.append(participant)
    
    return processed_data
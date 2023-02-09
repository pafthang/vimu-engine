import stripe
from fastapi import APIRouter, Request, Body

from config import settings
from models.api import APIResponse
from models.stripe import StripeSessionRequest
from pocketbase.pocketbase import Pocketbase

router = APIRouter()
pb = Pocketbase(settings.pocketbase_url, settings.pocketbase_admin_email, settings.pocketbase_admin_password)

@router.post("/stripe/session")
async def stripe_create_session(session_request: StripeSessionRequest):
    try:
        session = stripe.checkout.Session.create(
            success_url='https://vimu.app/dashboard/account/subscription?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://vimu.app/dashboard/account/subscription',
            customer_email=session_request.email,
            client_reference_id=session_request.user_id,
            mode='subscription',
            line_items=[{
                'price': session_request.price_id,
                'quantity': 1
            }],
        )
    except Exception as e:
        return APIResponse(status="error", data=None, error=str(e))

    return APIResponse(status="success", data=session.url, error=None)


@router.post('/stripe/webhook')
async def stripe_webhook_received(request: Request):
    webhook_secret = settings.stripe_webhook_secret
    raw_request_data = await request.body()
    signature = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(
            payload=raw_request_data, sig_header=signature, secret=webhook_secret)
        data = event['data']
    except Exception as e:
        return e

    event_type = event['type']
    data_object = data['object']

    if event_type == 'checkout.session.completed':
        user_id = data_object['client_reference_id']
        stripe_customer_id = data_object['customer']
        stripe_subscription_id = data_object['subscription']

        subscription = {'stripe_subscription_id': stripe_subscription_id, 'stripe_customer_id': stripe_customer_id,
                        'user': user_id, 'status': 'active'}

        pb.create('subscriptions', subscription)
    elif event_type == 'invoice.paid':
        stripe_subscription_id = data_object['subscription']
        subscription = pb.get_first_where('subscriptions', f"stripe_subscription_id='{stripe_subscription_id}'")

        if subscription is not None:
            subscription['status'] = 'active'
            pb.update('subscriptions', subscription)

    elif event_type == 'invoice.payment_failed':
        stripe_subscription_id = data_object['subscription']
        subscription = pb.get_first_where('subscriptions', f"stripe_subscription_id='{stripe_subscription_id}'")

        if subscription is not None:
            subscription['status'] = 'unpaid'
            pb.update('subscriptions', subscription)
    elif event_type == 'customer.subscription.updated':
        stripe_subscription_id = data_object.stripe_id
        subscription = pb.get_first_where('subscriptions', f"stripe_subscription_id='{stripe_subscription_id}'")
        status = data_object['status']

        if subscription is not None:
            subscription['status'] = status
            pb.update('subscriptions', subscription)
    elif event_type == 'customer.subscription.deleted':
        stripe_subscription_id = data_object.stripe_id
        subscription = pb.get_first_where('subscriptions', f"stripe_subscription_id='{stripe_subscription_id}'")

        print(subscription)
        if subscription is not None:
            pb.delete('subscriptions', subscription)
    else:
        print('Unhandled event type {}'.format(event_type))

    return APIResponse(status='success', data={}, error=None)


@router.get('/stripe/invoice')
async def stripe_list_invoices(customer_id: str):
    print(stripe.api_key)
    try:
        invoices = stripe.Invoice.list(customer=customer_id)
        return APIResponse(status="success", data=[i.to_dict() for i in invoices.data], error=None)
    except Exception as e:
        return APIResponse(status="error", data=None, error=e)

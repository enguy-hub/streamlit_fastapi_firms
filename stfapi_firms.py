import json
import requests
import streamlit as st

from services.firms_services import (
    get_account_status,
    get_current_transaction_count,
    convert_firms_csv_to_gdf,
    display_firms_points,
)

from models.firms_models import product_choice, country_code_list, days_ago_list


def set_state(i):
    st.session_state.stage = i


# @st.cache
def firms_points_map():
    if "stage" not in st.session_state:
        st.session_state.stage = 0

    if st.session_state.stage >= 0:

        inputed_product = st.selectbox(
            "Please the FIRMS product you would like to display",
            options=product_choice.__args__, 
            index=None, 
            placeholder="Select FIRMS product...",
            on_change=set_state, args=[1]
        )

    if st.session_state.stage >= 1:

        if inputed_product is not None:
            st.write(f"You have selected the FIRMS product: **{inputed_product}**")

            st.write(
                "\nFrom this list of country codes --> **https://firms.modaps.eosdis.nasa.gov/api/countries/?format=html**\n"
            )

            inputed_country_code = st.selectbox(
                "Please select the country would you like to see FIRMS points",
                options=country_code_list.__args__, 
                index=None, 
                placeholder="Select country code...",
                on_change=set_state, args=[2]
            )
            
    if st.session_state.stage >= 2:

        if inputed_country_code is not None:
            st.write(f"You have selected the country code: **{inputed_country_code}**")
        
            inputed_day = st.selectbox(
                "Please select how many days before today would you like to see FIRMS points",
                options=days_ago_list.__args__, 
                index=None, 
                placeholder="Select number of days...",
                on_change=set_state, args=[3]
            )

    if st.session_state.stage >= 3:

        if inputed_day is not None:
            st.write(f"You have selected the number of days: **{inputed_day}**")

            inputs = {
                "product": inputed_product, 
                "country": inputed_country_code,
                "days_ago": inputed_day,
            }

            post_url = requests.post(
                "http://localhost:8000/create/firms_csv_url", data=json.dumps(inputs)
            ).json()

            print(f"The FIRMS query URL is: \n{post_url}")
            # st_text_url = st.text(f"The FIRMS query URL is: \n{post_url}")

            if post_url is None:
                set_state(3)
            else:
                st.button("Query and Display FIRMS Data", on_click=set_state, args=[4])

    if st.session_state.stage >= 4:

        if post_url is not None:
            st.write(f'Querying FIRMS data ....')

            # test the query_result function
            start_count = get_current_transaction_count()
            country_gdf, country_centroid = convert_firms_csv_to_gdf(post_url)
            end_count = get_current_transaction_count()
            st.write("**%i** transactions were used" % (end_count - start_count))
            st.dataframe(country_gdf.astype(str))

            # check account status
            account_status = get_account_status()
            st.write("Current status of the FIRMS API usage")
            st.dataframe(account_status.astype(str))

            st.write(f'Displaying FIRMS data of "{inputed_country_code}" for the last **10 days** ...')
            display_firms_points(country_gdf, country_centroid)

            st.button("Try Again?", on_click=set_state, args=[0])


def main():

    APP_TITLE = "FastAPI & Streamlit - Demo Map"

    # Title
    st.title(APP_TITLE)
    st.header("Display FIRMS points for the selected country")

    # Start the app
    firms_points_map()


if __name__ == "__main__":
    main()

import os, time
from datetime import datetime

# yagmail to handle the email communication
import yagmail

# uuid used to generate unique hashs
import uuid

# dotenv library loads env files into the python environment.
from dotenv import load_dotenv

# gspread library handles the connectivity between python and Google Sheets
import gspread

# streamlit library holds all the web components to render the webpage  https://docs.streamlit.io/library/api-reference
import streamlit as st

# The feedback contents are imported from the file ./EssayContent.py
import EssayContent

# Load the env variables from .env
load_dotenv()

# defining constants
horizontal_line_red_dotted = "<hr style='border-top: 2px solid red;margin: 0' />"

gc = gspread.service_account_from_dict(
    {
        "type": os.environ.get("type"),
        "project_id": os.environ.get("project_id"),
        "private_key_id": os.environ.get("private_key_id"),
        "private_key": os.environ.get("private_key"),
        "client_email": os.environ.get("client_email"),
        "client_id": os.environ.get("client_id"),
        "auth_uri": os.environ.get("auth_uri"),
        "token_uri": os.environ.get("token_uri"),
        "auth_provider_x509_cert_url": os.environ.get("auth_provider_x509_cert_url"),
        "client_x509_cert_url": os.environ.get("client_x509_cert_url"),
        "universe_domain": os.environ.get("universe_domain"),
    }
)

sh = None
login_info_sheet = None
data_sheet = None

# the entire file runs for every page event and google sheets has limitation to connect.
# With the below condition the sheets are loaded once
if sh == None:
    sh = gc.open_by_url(os.environ.get("google_sheet"))

if login_info_sheet == None:
    login_info_sheet = sh.get_worksheet(0)

if data_sheet == None:
    data_sheet = sh.get_worksheet(1)


# define helper functions


# To insert a new element, the next available row index is calculated
def api_get_available_index(worksheet):
    list_of_lists = worksheet.get_all_values()
    return len(list_of_lists) + 1


# insert the time student logs in
# also decide the instruction condition based on the odd or even login order
def api_record_login_time():
    r = api_get_available_index(login_info_sheet)

    st.session_state["show_instructions_first"] = r % 2 == 0

    login_info_sheet.update(
        r"A{}:C{}".format(r, r),
        [
            [
                st.session_state["student_email"],
                st.session_state["student_ID"],
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            ]
        ],
    )


# returns boolean
# verify if the student email or ID is already present in the data sheet. returns true if present
def checkStudentDetailsInSheet():
    student_email = st.session_state["student_email"]
    student_ID = st.session_state["student_ID"]
    emails = data_sheet.col_values(2)
    studentIds = data_sheet.col_values(3)

    if student_email.strip() in emails or student_ID.strip() in studentIds:
        st.warning("You have already attended the survey. Thank you for participating")
        return True
    return False


# insert the recorded values
def api_record_results(original, ai, open_feedback):
    allData = data_sheet.get_all_values()
    index = 1

    # iterate the rows in data sheet and check if second column(email column) is empty
    # if empty the amazon voucher is taken and values are updated into the row
    for items in allData:
        print(items)
        if items[1] == "":
            st.session_state["amazon_voucher"] = items[0]
            break
        index += 1

    data_sheet.update(
        r"B{}:G{}".format(index, index),
        [
            [
                st.session_state["student_email"],
                st.session_state["student_ID"],
                original,
                ai,
                open_feedback,
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            ]
        ],
    )
    # st.experimental_rerun()


# variables for yagmail configurations
user = os.environ.get("gmail_id")
app_password = os.environ.get("gmail_app_password")  # a token for gmail

# initialize state variables for streamlit
# https://docs.streamlit.io/library/api-reference/session-state
if "loading" not in st.session_state:
    st.session_state["loading"] = False

if "email_sent_flag" not in st.session_state:
    st.session_state["email_sent_flag"] = False

if "web_page" not in st.session_state:
    st.session_state["web_page"] = "Login_page"

# the order of pages is below:
# Login_page --> Instructions_page --> Consent_Page(Do_not_consent_page) --> (Conditional_Instructions_page) --> Survey_page --> (Conditional_Instructions_page) --> Voucher_page

if "amazon_voucher" not in st.session_state:
    st.session_state["amazon_voucher"] = False

if "student_ID" not in st.session_state:
    st.session_state["student_ID"] = False

if "student_email" not in st.session_state:
    st.session_state["student_email"] = False

if "system_password" not in st.session_state:
    st.session_state["system_password"] = uuid.uuid4().hex[:8]

if "show_instructions_first" not in st.session_state:
    st.session_state["show_instructions_first"] = True


# trigger email to verify login and send passcode
def handleSubmit():
    content = r"Hi, {}({}). Your pass code for the feeback form is {}".format(
        st.session_state["student_email"].strip(),
        st.session_state["student_ID"].strip(),
        st.session_state["system_password"].strip(),
    )
    print(content)

    # check if voucher is sent already
    if checkStudentDetailsInSheet() == False:
        # if no details present,proceed to send
        subject = "QUB AI Assist Feeback Form"

        with yagmail.SMTP(user, app_password) as yag:
            yag.send(st.session_state["student_email"], subject, content)
            print("Sent email successfully")
        st.session_state["email_sent_flag"] = True
        # experimental rerun is like soft refresh to the application to force rendering again
        st.experimental_rerun()


# delivers the final email with thank you message and voucher code
def sendFinalEmail():
    content = r"We hightly appreciate your efforts in participating in the feedback. Your amazon voucher code is {}".format(
        st.session_state["amazon_voucher"]
    )

    with yagmail.SMTP(user, app_password) as yag:
        yag.send(
            st.session_state["student_email"],
            "Thank you for participating in the Feedback ",
            content,
        )
        print("Sent email successfully")
    st.session_state["loading"] = True


# decide the conditional render of instructions and store the records
def handleFinalSubmit(original, ai, open_feedback):
    api_record_results(original, ai, open_feedback)
    time.sleep(3)

    if st.session_state["show_instructions_first"]:
        st.session_state["web_page"] = "Voucher_page"
    else:
        st.session_state["web_page"] = "Conditional_Instructions_page"
    st.experimental_rerun()


# UI components
# the top level of UI code is an IF else ladder which controls the pages

# login page starts
if st.session_state["web_page"] == "Login_page":
    # title renders a h1 element
    st.title(
        "Welcome to the Survey by the Department of Psychology.",
    )

    # initialize the login form, the form values are stored in state
    with st.form("login_form"):
        st.write(
            "Please enter your university email address and student ID to proceed:"
        )
        st.session_state["student_email"] = st.text_input(
            "Email Address",
            "",
            key="email_inp",
            disabled=st.session_state["email_sent_flag"],
        )
        st.session_state["student_ID"] = st.text_input(
            "Student ID",
            "",
            key="std_id_inp",
            disabled=st.session_state["email_sent_flag"],
        )

        submit_btn = st.form_submit_button(
            "Submit", disabled=st.session_state["email_sent_flag"]
        )

        if submit_btn:
            handleSubmit()

    if st.session_state["email_sent_flag"] != False:
        st.success(
            "A pass code is sent to your email address. Please enter the password to proceed. If you cant find email please check spam folder too.",
            icon="✅",
        )
        password = st.text_input("Pass code", "", type="password")
        login_btn = st.button("Login", key="login")

        # on login button click user passcode and system passcode, if match record the time and move to next page
        if login_btn:
            if password == st.session_state["system_password"]:
                api_record_login_time()
                st.session_state["web_page"] = "Instructions_page"
                # sometimes trigger rerender to navigate
                st.experimental_rerun()
            else:
                st.error("Incorrect Pass code! Please try again", icon="🚨")
# login page ends

# survey page starts
elif st.session_state["web_page"] == "Survey_page":
    # set page to maximum width, to render surveys and input fields
    st.set_page_config(layout="wide")

    # beginning of sidebar
    with st.sidebar:
        st.markdown(
            horizontal_line_red_dotted,
            unsafe_allow_html=True,
        )
        original_feedback = st.slider(
            "Please rate the **original** version of the feebdack you received. \n",
            min_value=0,
            max_value=100,
            step=1,
            disabled=st.session_state["amazon_voucher"] != False,
        )
        st.markdown(
            horizontal_line_red_dotted,
            unsafe_allow_html=True,
        )
        ai_feedback = st.slider(
            "Please rate the **alternative** version of the feedback you received.",
            min_value=0,
            max_value=100,
            step=1,
            disabled=st.session_state["amazon_voucher"] != False,
        )
        st.markdown(
            horizontal_line_red_dotted,
            unsafe_allow_html=True,
        )
        original_readability = st.slider(
            "Please rate the readability of the **original** version.",
            min_value=0,
            max_value=100,
            step=1,
            disabled=st.session_state["amazon_voucher"] != False,
        )
        st.markdown(
            horizontal_line_red_dotted,
            unsafe_allow_html=True,
        )

        ai_readability = st.slider(
            "Please rate the readability of the **alternate** version.",
            min_value=0,
            max_value=100,
            step=1,
            disabled=st.session_state["amazon_voucher"] != False,
        )
        st.markdown(
            horizontal_line_red_dotted,
            unsafe_allow_html=True,
        )

        open_feedback = st.text_area(
            "Your thoughts on reviewing these feedbacks", "", height=250
        )

        final_submit = st.button(
            "Submit Rating",
            key="final",
            type="primary",
            disabled=st.session_state["amazon_voucher"] != False,
        )

        if final_submit:
            handleFinalSubmit(original_feedback, ai_feedback, open_feedback)
    # end of sidebar

    # start of main content
    st.header("Feedback on your 2nd PSY2008 essay")

    # collapsible content rendered with expander
    with st.expander("**Lecturer's Feedback**"):
        st.markdown(
            EssayContent.prof_feedback,
            unsafe_allow_html=True,
        )

    with st.expander("**Enhanced AI Feedback, based on Lecturer's Feedback**"):
        st.markdown(
            EssayContent.ai_feedback,
            unsafe_allow_html=True,
        )
# end of main content
# survey page ends

# voucher page starts
elif st.session_state["web_page"] == "Voucher_page":
    st.balloons()
    st.markdown(
        '<h1 style="text-align: center; margin-top: 3rem;">Thank you for taking the survey</h1>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h4 style='text-align: justify;'>You have now completed the study. As mentioned initially, we would like to express our gratitude for your taking part in our study by giving you a £15 Amazon voucher as compensation for your time and effort. </h4>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "Here is the code for your voucher (we will also send you an email with the code so that you do not have to write it down):",
    )

    st.markdown(
        r'<div style="text-align: center;"><span class="amazon_voucher">{}</span></div>'.format(
            st.session_state["amazon_voucher"]
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='text-align: center;'><br/><br/>Thanks again! You can now close your browser.</div>",
        unsafe_allow_html=True,
    )
    sendFinalEmail()
# voucher page ends

# Instructions page starts
elif st.session_state["web_page"] == "Instructions_page":
    st.markdown(
        """ # Evaluating the quality of feedback on student assignments

You are being invited to take part in a research study looking at students’ evaluation of the feedback they receive on their written assignments.

<strong>You were chosen as a participant because you are a Year 1 student in the BSc Psychology undergraduate programme at QUB.
Before you decide to take part in this study it is important for you to understand what the research will involve. Please take time to read the following information and do not hesitate to contact us should you require any further details.</strong>

In this survey, we will show you the feedback you received on one of your written assignments, namely your Semester 2 essay on individual differences. We will also show you an alternative version of that feedback.

Once you have read both versions of the feedback, we will ask you to rate their quality using four statements each.
The study should take <span style="color:red;font-weight:bold">no more than 20 minutes</span> to complete. So please take the time and read both versions of the feedback thoroughly before rating their quality. <span style="color:red;font-weight:bold">You will receive an Amazon voucher worth £15 for your time. Please continue until the very end of this questionnaire to receive your compensation.</span>

Your participation is entirely voluntary, and you have the right to withdraw at any time during the study by closing this webpage. If you decide to close this webpage before the end of the questionnaire, your partial response will be deleted as a matter of course. Once you have completed the study, you will not be able to withdraw your data.
Please note: Your participation in our study will be treated with confidentiality. The data we gather from you and other participants during this study will be fully anonymised prior to analysis so that no one will be able to link the data to you personally. In addition, we will not share your evaluations with your tutors who provided the feedback. Therefore, you can be completely honest in your evaluations.
Since the data we collect from you may be of interest to other researchers, we will publish it on a publicly accessible online data repository. At that point, anyone will have access to your anonymised (i.e., non-identifiable) data.

Our research depends crucially on the generous help of participants like yourself. We hope that you can assist us with this project.

If you have any further queries, please do not hesitate to contact Dr Thomas Schultze at <span style="color:red">t.schultze@qub.ac.uk</span>
 """,
        unsafe_allow_html=True,
    )

    clicked = st.button("Proceed", type="primary")

    if clicked:
        st.session_state["web_page"] = "Consent_page"
        st.experimental_rerun()
# Instructions page ends

# Consent page starts
elif st.session_state["web_page"] == "Consent_page":
    st.header("Consent to taking part in the study.")
    st.markdown(
        "Please tick each statement to indicate your agreement. If left unmarked, you will not be able to proceed to the questionnaire."
    )

    agree1 = st.checkbox(
        "1.	I have read and understood the information about the study."
    )
    agree2 = st.checkbox(
        "2.	I understand that my participation is entirely voluntary and that I am free to withdraw during the study at any time without giving a reason."
    )
    agree3 = st.checkbox(
        "3.	I understand that my involvement in this research is strictly anonymous and that my participating is confidential. "
    )
    agree4 = st.checkbox(
        "4.	I understand that my anonymised data will be published in a public repository."
    )
    agree5 = st.checkbox(
        "5.	I consent to my data being made available anonymously in a public repository."
    )
    agree6 = st.checkbox("6.	I consent to participate in this study.")

    if st.button(
        "I do Consent, Proceed.",
        disabled=not agree1
        or not agree2
        or not agree3
        or not agree4
        or not agree5
        or not agree6,
        type="primary",
    ):
        if st.session_state["show_instructions_first"]:
            st.session_state["web_page"] = "Conditional_Instructions_page"
        else:
            st.session_state["web_page"] = "Survey_page"
        st.experimental_rerun()

    if st.button(
        "I do not Consent",
        disabled=agree1 and agree2 and agree3 and agree4 and agree5 and agree6,
    ):
        st.session_state["web_page"] = "Do_not_consent_page"
        st.experimental_rerun()
# Consent page ends

# No Consent page starts
elif st.session_state["web_page"] == "Do_not_consent_page":
    st.markdown(
        '<h1 style="text-align: center; margin-top: 2rem;">&nbsp;</h1>',
        unsafe_allow_html=True,
    )
    st.subheader(
        "You have not provided consent to take part in our study. Nonetheless, we thank you for considering to take part."
    )
    st.subheader("You can now close your browser.")
    st.markdown(
        """If you withheld consent to take part accidentally and would like to participate, please contact <br/>
        Dr Thomas Schultze-Gerlach (t.schultze@qub.ac.uk)""",
        unsafe_allow_html=True,
    )
# No Consent page ends

# Conditional Instructions page starts
elif st.session_state["web_page"] == "Conditional_Instructions_page":
    if st.session_state["show_instructions_first"]:
        st.header("Instructions:")
        st.markdown(
            "In this study, we will show you the feedback you received on your PSY1008 essay on individual differences where you compared the personality theories of Freud and Rogers."
        )
        st.markdown(
            "In addition to the actual feedback you received from your tutor, we will show you an alternative version of that feedback."
        )
        st.markdown(
            """We would like to briefly explain how we created the alternative version of the feedback. To create it, we took the original feedback provided by your tutor and fed it into an AI, more specifically, a large language model (LLM). The LLM we used was ChatGPT, which you might be familiar with. We instructed the AI to take the original feedback and make it constructive and encouraging . The result is what we call **AI-augmented feedback**. AI-augmented feedback differs from AI-generated feedback in that it is based on human evaluation of your essay instead of an AI attempting to evaluate and provide feedback on its own."""
        )
        st.markdown(
            """We would kindly ask you to read both versions of the feedback on your essay thoroughly. Once you have read them, please rate each version using a set of four statements. Please also state which version of the feedback you would prefer if you had to choose between them and describe briefly why you prefer one version of the feedback over the other."""
        )
        st.markdown(
            "**Important:** Remember that your responses will be treated confidentially. That is, your tutor will not see how you rated their feedback, and you can be completely honest in your assessment of that feedback."
        )
    else:
        st.markdown(
            '<h1 style="text-align: center; margin-top: 2rem;">&nbsp;</h1>',
            unsafe_allow_html=True,
        )
        st.header("Thank you for taking part in this study.")
        st.markdown(
            "Before, we tell you what the aim of our study was, we would first like to briefly explain how we created the alternative version of the feedback you just read. To create it, we took the original feedback provided by your tutor and fed it into an AI, more specifically, a large language model (LLM). The LLM we used was ChatGPT, which you might be familiar with. We instructed the AI to take the original feedback and make it constructive and encouraging. The result is what we call **AI-augmented feedback**. AI-augmented feedback differs from AI-generated feedback in that it is based on human evaluation of your essay instead of an AI attempting to evaluate and provide feedback on its own."
        )
        st.markdown(
            "The aim of our study was to investigate how students would evaluate AI-augmented feedback relative to the original feedback they actually received and which the augmented feedback was based on. The reason why we study AI-augmented feedback is because we want to provide our students with the best possible feedback. Augmenting human feedback with AI might be a way to improve the quality of feedback while making sure that feedback still entails human evaluation of the assignment."
        )
        st.markdown(
            "By taking part in our study, you have provided valuable information on the perceived quality of AI-augmented feedback relative to purely human feedback. Thank you again for taking the time!"
        )

    clicked = st.button(
        "Okay, I understand.",
        type="primary",
    )
    if clicked:
        if st.session_state["show_instructions_first"]:
            st.session_state["web_page"] = "Survey_page"
        else:
            st.session_state["web_page"] = "Voucher_page"
        st.experimental_rerun()
# Conditional Instructions page ends


# static styles for the page
title_alignment = """
<style>
#the-title {
  text-align: center
}
.block-container {
padding: 2rem 1rem;
}
#feedback-on-your-2nd-psy2008-essay{
border-bottom: 1px solid silver;
text-align: center
}
.stSlider  p{
margin-bottom: 15px
}

.stSlider  > div{
margin-bottom: 20px
}
.amazon_voucher{
text-align: center; 
border: 1px solid black; 
border-radius: 10px;
padding: 10px;
font-weight: bold;
font-size: 3rem;
}
#welcome-to-the-survey-by-department-of-psychology{
text-align: center;
}
</style>
"""
st.markdown(title_alignment, unsafe_allow_html=True)

# js_scripts = """
# <script>
# const onConfirmRefresh = function (event) {
#   event.preventDefault();
#   return event.returnValue = "Are you sure you want to leave the page?";
# }

# window.addEventListener("beforeunload", onConfirmRefresh, { capture: true });
# </script>
# """
# components.html(js_scripts, height=10)
# st.markdown(js_scripts, unsafe_allow_html=True)
